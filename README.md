# json-to-pdf

This project provides a Python application that converts JSON data into a PDF document, including the generation of Data Matrix and barcode images. The application is designed to be run in an AWS Lambda environment, utilizing various libraries for image processing and PDF generation.

## Features

- **JSON to PDF Conversion**: Takes JSON input and generates a PDF document.
- **Data Matrix Generation**: Creates Data Matrix images from specified data in the JSON.
- **Barcode Generation**: Generates barcode images from specified data in the JSON.
- **SVG Template Support**: Uses an SVG template to format the output PDF, allowing for customizable layouts.

## Requirements

- Python 3.9
- AWS Lambda environment
- Required Python packages listed in `requirements.txt`

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```

2. Build the Docker image:
   ```bash
   docker build -t json-to-pdf .
   ```

3. Run the Docker container (if testing locally):
   ```bash
   docker run -p 9000:8080 json-to-pdf
   ```

## Usage

To use the application, you need to provide a JSON payload that includes:

- `template_path`: The S3 path to the SVG template.
- `variables`: A dictionary of variables to replace in the SVG.
- `barcodes`: A list of barcode data to generate.
- `matrixcodes`: A list of Data Matrix data to generate.
- `images`: A list of image URLs to include in the PDF.

### Example JSON Payload

```json
{
    "template_path": "s3://your-bucket/template.svg",
    "variables": {
        "orderItemId": "12345",
        "customerName": "John Doe",
        "date": "2023-10-01"
    },
    "barcodes": [
        {
            "id": "barcode1",
            "data": "123456789"
        }
    ],
    "matrixcodes": [
        {
            "id": "matrix1",
            "data": "987654321"
        }
    ],
    "images": [
        {
            "id": "image_1",
            "source": "https://example.com/image.png"
        }
    ]
}

## Running the Application

You can deploy the application to AWS Lambda and invoke it with the JSON payload. The generated PDF will be uploaded to the specified S3 bucket.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.