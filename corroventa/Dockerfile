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

# Pin dependency releases (override via build.yaml args).
ARG PROTOCOL_REPO=https://github.com/mberglundmx/corroventa-protocol.git
ARG PROTOCOL_REF=v0.3.0
ARG YARDSTICK_REPO=https://github.com/mberglundmx/corroventa-radio-yardstick.git
ARG YARDSTICK_REF=v0.2.0

# Build C++ protocol + pybind11 from a tagged release
RUN git clone --depth 1 --branch "${PROTOCOL_REF}" "${PROTOCOL_REPO}" /tmp/corroventa-protocol \
 && cmake -S /tmp/corroventa-protocol -B /tmp/corroventa-protocol/build \
      -DCORROVENTA_PROTOCOL_BUILD_PYTHON=ON \
      -DCORROVENTA_PROTOCOL_BUILD_TESTS=OFF \
      -DCMAKE_BUILD_TYPE=Release \
 && cmake --build /tmp/corroventa-protocol/build -j"$(nproc)" \
 && cp /tmp/corroventa-protocol/build/corroventa_protocol*.so /opt/corroventa/ \
 && PYTHONPATH=/opt/corroventa python3 -c "import corroventa_protocol as p; print('protocol OK', '${PROTOCOL_REF}', p.decode_frame)" \
 && rm -rf /tmp/corroventa-protocol

# Yard Stick transport package from a tagged release
RUN git clone --depth 1 --branch "${YARDSTICK_REF}" "${YARDSTICK_REPO}" /tmp/yardstick \
 && mkdir -p /opt/corroventa/vendor \
 && cp -a /tmp/yardstick/corroventa_radio_yardstick /opt/corroventa/vendor/ \
 && PYTHONPATH=/opt/corroventa:/opt/corroventa/vendor python3 -c "import corroventa_radio_yardstick as y; print('yardstick OK', '${YARDSTICK_REF}')" \
 && rm -rf /tmp/yardstick

COPY corroventa_gateway/ /opt/corroventa/corroventa_gateway/
COPY run.sh /run.sh
RUN chmod a+x /run.sh \
 && PYTHONPATH=/opt/corroventa:/opt/corroventa/vendor python3 -c "import corroventa_gateway; print('gateway OK')"

ENV PYTHONPATH=/opt/corroventa:/opt/corroventa/vendor
ENV PYTHONUNBUFFERED=1

CMD ["/run.sh"]
