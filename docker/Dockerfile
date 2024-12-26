FROM public.ecr.aws/lambda/python:3.9

# Install system dependencies
RUN yum install -y \
    gcc \
    make \
    wget \
    tar \
    gzip \
    automake \
    libtool

# Install libdmtx from source
RUN wget https://github.com/dmtx/libdmtx/archive/refs/tags/v0.7.5.tar.gz && \
    tar -xzvf v0.7.5.tar.gz && \
    cd libdmtx-0.7.5 && \
    ./autogen.sh && \
    ./configure && \
    make && \
    make install && \
    cd .. && \
    rm -rf libdmtx-0.7.5 v0.7.5.tar.gz

# Copy function code and required files
COPY app.py ${LAMBDA_TASK_ROOT}
COPY entry.sh ${LAMBDA_TASK_ROOT}

# Ensure the app.py and entry.sh scripts are executable
RUN chmod +x ${LAMBDA_TASK_ROOT}/app.py ${LAMBDA_TASK_ROOT}/entry.sh

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Set the working directory
WORKDIR ${LAMBDA_TASK_ROOT}

# Set the library path to include /usr/local/lib
ENV LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH

# Set the entrypoint to entry.sh
ENTRYPOINT ["./entry.sh"]

# Set the CMD to your handler
CMD ["app.handler"]
