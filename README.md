BTSProxy
=============

BTSProxy is a simple websocket proxy for bitshares, which allows user to request their account history (and more afterwards) via elasticsearch transparently.
It can help the witness\_node to reduce the stress of tracking account histories for every user.

BTSProxy is currently under heavy development: it lacks reviews / documents / tests. So, try it AT YOUR OWN RISK.

How to use
---------------
A TLS certificate is strongly recommended. Random issues may happen if you use ws:// (we are investigating).

Deploy without docker:
    git clone https://github.com/Tydus/btsproxy
    cd btsproxy
    python3 install
    export WS_URL=wss://...
    export ES_URL=https://...
    export SSL_CERT=/path/to/cert
    export SSL_KEY=/path/to/key
    export LISTEN_PORT=8080
    screen -dm -S btsproxy btsproxy

Deploy with docker:
    docker run -d -e "..." -v /path/to/cert:/cert tydus/btsproxy

Pitfalls
---------------
Due to the "1.11.xxx" representation of the object-ids in elasticsearch, to retrieve account histories correctly is far from trivial, and my solution is far from elegant. However, we did it.

This is a temporary solution.
After the elasticsearch plugin is reworked, the performance will be decent and the code will look better.

The official bitshares-ui also has issues of only retrieving top 100 lines of account historiy, which renders this proxy useless.

See also:

[core#1103](https://github.com/bitshares/bitshares-core/issues/1103#issuecomment-402699689)

[ui#1665](https://github.com/bitshares/bitshares-ui/issues/1665)
