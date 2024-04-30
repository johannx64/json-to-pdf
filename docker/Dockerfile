FROM public.ecr.aws/lambda/python:3.9

# Install system dependencies
RUN yum install -y freetype-devel libjpeg-turbo-devel zlib-devel

# Copy function code
COPY lambda_function.py ${LAMBDA_TASK_ROOT}

# Install Python dependencies
COPY requirements.txt .
RUN python3.9 -m pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Set the CMD to your handler
CMD ["lambda_function.handler"]