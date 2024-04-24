FROM public.ecr.aws/lambda/python:3.7.2024.04.17.17

# Copy requirements.txt
COPY requirements.txt ${LAMBDA_TASK_ROOT}
#COPY install-browsers.sh /tmp/

# Install build tools
RUN yum update -y && \
    yum groupinstall -y "Development Tools" && \
    yum install -y gcc

# Install the specified packages
RUN pip install -r requirements.txt

# Copy function code
COPY lambda_function.py ${LAMBDA_TASK_ROOT}

# Set the CMD to your handler (could also be done as a parameter override outside of the Dockerfile)
CMD [ "lambda_function.handler" ]
