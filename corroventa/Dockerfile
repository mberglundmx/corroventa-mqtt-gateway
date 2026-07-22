ARG BUILD_FROM
FROM $BUILD_FROM

# gcc + libusb-dev: pyusb on musl finds libusb via the linker
# (see pyusb#537). rfcat provides rflib for Yard Stick One.
RUN apk add --no-cache \
    build-base \
    cmake \
    gcc \
    git \
    libusb \
    libusb-dev \
    linux-headers \
    python3-dev

ENV LD_LIBRARY_PATH=/lib:/usr/lib

WORKDIR /opt/corroventa

COPY requirements.txt .
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt \
 && python3 -c "from rflib import RfCat; print('rflib OK', RfCat)"

# Build C++ protocol + pybind11 module (source of truth)
COPY vendor/corroventa-protocol /tmp/corroventa-protocol
RUN cmake -S /tmp/corroventa-protocol -B /tmp/corroventa-protocol/build \
      -DCORROVENTA_PROTOCOL_BUILD_PYTHON=ON \
      -DCORROVENTA_PROTOCOL_BUILD_TESTS=OFF \
      -DCMAKE_BUILD_TYPE=Release \
 && cmake --build /tmp/corroventa-protocol/build -j"$(nproc)" \
 && cp /tmp/corroventa-protocol/build/corroventa_protocol*.so /opt/corroventa/ \
 && PYTHONPATH=/opt/corroventa python3 -c "import corroventa_protocol as p; print('protocol OK', p.decode_frame)" \
 && rm -rf /tmp/corroventa-protocol

COPY vendor/corroventa_radio_yardstick /opt/corroventa/vendor/corroventa_radio_yardstick
COPY corroventa_gateway/ /opt/corroventa/corroventa_gateway/
COPY run.sh /run.sh
RUN chmod a+x /run.sh \
 && PYTHONPATH=/opt/corroventa:/opt/corroventa/vendor python3 -c "import corroventa_gateway; print('gateway OK')"

ENV PYTHONPATH=/opt/corroventa:/opt/corroventa/vendor
ENV PYTHONUNBUFFERED=1

CMD ["/run.sh"]
