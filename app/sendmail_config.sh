#!/bin/sh
# set host in hosts
line=$(head -n 1 /etc/hosts)
line2=$(echo $line | awk '{print $2}')
echo "$line $line2.localdomain" >> /etc/hosts

apt-get install -y sendmail sendmail-cf m4 \
    && hostname >> /etc/mail/relay-domains \
    && m4 /etc/mail/sendmail.mc > /etc/mail/sendmail.cf

#remove localhost limit
sed -i -e "s/Port=smtp,Addr=127.0.0.1, Name=MTA/Port=smtp, Name=MTA/g" /etc/mail/sendmail.mc
sendmail -bd
