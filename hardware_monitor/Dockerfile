ARG BUILD_FROM
FROM $BUILD_FROM

RUN apk add --no-cache \
    bash \
    procps \
    lm-sensors

RUN pip install --no-cache-dir flask psutil

RUN mkdir -p /app/templates

COPY app/ /app/
COPY run.sh /run.sh
RUN chmod +x /run.sh

WORKDIR /app
CMD ["/run.sh"]
