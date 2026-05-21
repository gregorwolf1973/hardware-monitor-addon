ARG BUILD_FROM
FROM $BUILD_FROM

RUN apk add --no-cache procps lm-sensors

RUN pip3 install --no-cache-dir --break-system-packages flask psutil

COPY app/ /app/
COPY run.sh /run.sh
RUN chmod +x /run.sh

WORKDIR /app

# Bypass HA's s6-overlay entrypoint – s6 requires PID 1, incompatible with host_pid:true
ENTRYPOINT []
CMD ["/run.sh"]
