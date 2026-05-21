ARG BUILD_FROM
FROM $BUILD_FROM

RUN apk add --no-cache \
    python3 \
    py3-pip \
    bash \
    lm-sensors \
    procps

RUN pip3 install --break-system-packages flask psutil

RUN mkdir -p /app/templates

COPY app/ /app/
COPY run.sh /run.sh
RUN chmod +x /run.sh

WORKDIR /app
CMD ["/run.sh"]
