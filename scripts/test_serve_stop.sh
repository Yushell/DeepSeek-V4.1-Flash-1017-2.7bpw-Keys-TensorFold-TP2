#!/usr/bin/env bash
# Offline test of the recipe launcher's stop(): runs the shipped function text (extracted verbatim from serve.sh)
# against a fake docker and scratch log directories. Touches no node, no container and no server.
#
#   scripts/test_serve_stop.sh /path/to/serve.sh
#
# It covers patches/0004-serve-keep-logs.patch: each node keeps its run's log before the container is removed, a rank
# that ended by itself (node_run.sh starts the container with --rm, so only its tee'd file is left) keeps that file,
# an empty file is left alone, and an unreachable node does not stop the other node from being stopped.
set -u
SERVE=${1:?path to serve.sh}
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
fails=0
ok() {
  if [ "$2" = "$3" ]; then printf 'PASS  %s\n' "$1"; else printf 'FAIL  %s  want=[%s] got=[%s]\n' "$1" "$2" "$3"; fails=$((fails + 1)); fi
}

# A fake docker. Its state is the current directory (one directory per fake node): the file ./exists means the
# container is there; every call is appended to ./calls.
mkdir -p "$T/bin"
cat > "$T/bin/docker" <<'EOF'
#!/usr/bin/env bash
echo "$*" >> calls
case "$1" in
  inspect) [ -e exists ] ;;
  logs)
    [ -e exists ] || { echo "Error response from daemon: No such container: $3" >&2; exit 1; }
    [ "$2" = "-t" ] || { echo "logs called without -t" >&2; exit 2; }
    printf '2024-01-01T00:00:00.000000000Z line one\n2024-01-01T00:00:01.000000000Z line two\n' ;;
  rm) rm -f exists; exit 0 ;;
  *) exit 0 ;;
esac
EOF
chmod +x "$T/bin/docker"

# The shipped function, verbatim, plus what it needs in scope. Each "node" is a directory with its own logs/.
eval "$(sed -n '/^stop() {/,/^}/p' "$SERVE")"
N=(nodeA nodeB)
LOG_DIR=logs
via() { ( cd "$T/$1" && PATH="$T/bin:$PATH" bash -c "$2" ); }

fresh() { rm -rf "$T/nodeA" "$T/nodeB"; mkdir -p "$T/nodeA/logs" "$T/nodeB/logs"; }
count() { find "$1" -maxdepth 1 -name "$2" | wc -l | tr -d ' '; }

echo "=== 1. both ranks running, each with its log file"
fresh
for n in nodeA nodeB; do touch "$T/$n/exists"; printf 'engine line 1 on %s\nengine line 2\n' "$n" > "$T/$n/logs/tp2-lane.log"; done
stop; rc=$?
ok "stop returns 0" 0 "$rc"
for n in nodeA nodeB; do
  ok "$n: container removed" "no" "$([ -e "$T/$n/exists" ] && echo yes || echo no)"
  ok "$n: one docker log kept" 1 "$(count "$T/$n/logs" 'tp2-lane.*.docker.log')"
  ok "$n: docker log has docker's timestamps" 2 "$(grep -c '^2024-01-01T00:00:0' "$T/$n/logs"/tp2-lane.*.docker.log)"
  ok "$n: one run log kept" 1 "$(find "$T/$n/logs" -maxdepth 1 -name 'tp2-lane.*.log' ! -name '*.docker.log' | wc -l | tr -d ' ')"
  ok "$n: run log keeps its content" "engine line 1 on $n" "$(head -n 1 "$(find "$T/$n/logs" -maxdepth 1 -name 'tp2-lane.*.log' ! -name '*.docker.log')")"
  ok "$n: tp2-lane.log is free for the next run" "no" "$([ -e "$T/$n/logs/tp2-lane.log" ] && echo yes || echo no)"
  ok "$n: the log was read before the container was removed" "inspect tp2-lane|logs -t tp2-lane|rm -f tp2-lane" "$(paste -sd'|' "$T/$n/calls")"
done

echo "=== 2. a rank that ended by itself (--rm took the container): only its file is left"
fresh
printf 'last words of a run that ended by itself\n' > "$T/nodeA/logs/tp2-lane.log"
stop; rc=$?
ok "stop returns 0" 0 "$rc"
ok "nodeA: no docker log (no container)" 0 "$(count "$T/nodeA/logs" 'tp2-lane.*.docker.log')"
ok "nodeA: the run log is kept" "last words of a run that ended by itself" "$(cat "$T/nodeA/logs"/tp2-lane.2*.log 2>/dev/null)"
ok "nodeA: rm still called" "yes" "$(grep -q '^rm -f tp2-lane$' "$T/nodeA/calls" && echo yes || echo no)"

echo "=== 3. nothing to keep: no container, no file"
ok "nodeB: no files appear" 0 "$(find "$T/nodeB/logs" -type f | wc -l | tr -d ' ')"
ok "nodeB: rm still called" "yes" "$(grep -q '^rm -f tp2-lane$' "$T/nodeB/calls" && echo yes || echo no)"

echo "=== 4. an empty log file is left alone; a missing log directory does not block the stop"
fresh
: > "$T/nodeA/logs/tp2-lane.log"
rm -rf "$T/nodeB/logs"; touch "$T/nodeB/exists"
stop; rc=$?
ok "stop returns 0" 0 "$rc"
ok "nodeA: no rotated copy of an empty file" 0 "$(find "$T/nodeA/logs" -maxdepth 1 -name 'tp2-lane.2*' | wc -l | tr -d ' ')"
ok "nodeB: container removed without a log directory" "no" "$([ -e "$T/nodeB/exists" ] && echo yes || echo no)"

echo "=== 5. a node that cannot be reached does not stop the other from being stopped, and stop says so"
fresh
touch "$T/nodeB/exists"; printf 'x\n' > "$T/nodeB/logs/tp2-lane.log"
via() { if [ "$1" = nodeA ]; then return 255; fi; ( cd "$T/$1" && PATH="$T/bin:$PATH" bash -c "$2" ); }
stop; rc=$?
ok "stop returns 1 (a node was not reached)" 1 "$rc"
ok "nodeB: container removed" "no" "$([ -e "$T/nodeB/exists" ] && echo yes || echo no)"
ok "nodeB: run log kept" 1 "$(find "$T/nodeB/logs" -maxdepth 1 -name 'tp2-lane.2*.log' ! -name '*.docker.log' | wc -l | tr -d ' ')"

echo
if [ "$fails" -eq 0 ]; then echo "all tests passed"; else echo "$fails test(s) failed"; exit 1; fi
