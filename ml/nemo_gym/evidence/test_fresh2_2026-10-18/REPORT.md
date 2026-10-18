# Initial fresh2 launch: infrastructure failure

All 378 attempts ended in ConnectError; no request reached the model.
Each arm has raw rewards 0, 0, 0 /42; mean 0, range 0–0, all seven families 0/18,
126 provider errors per arm, zero repairs. These are infrastructure outcomes,
not a model comparison. Raw traces, configurations, seal and opening marker
are retained. The shell launch incorrectly continued after failed readiness.

The user authorized one complete relaunch, documented separately. No failed
case was selectively retried and none of these records was overwritten.
