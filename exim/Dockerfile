FROM elsdoerfer/exim-sender

RUN (echo disable_ipv6=true) >exim.conf.tmp && \
    cat /etc/exim4/exim4.conf >>exim.conf.tmp && \
    mv exim.conf.tmp /etc/exim4/exim4.conf
