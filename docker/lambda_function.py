import os
import io
import json
import logging
import boto3
import zipfile
from PIL import Image, ImageDraw
from pyzbar.pyzbar import encode, decode
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

class LambdaMethodHandler:
    def handle_request(self, input, context):
        context.logger.info(f"Input: {input}")
        return self.handle_json_request(input, context)

    def handle_json_request(self, input, context):
        output = {}
        try:
            items = input.get("items")
            order_id = input.get("orderId")
            dir_path = "/tmp"
            if not os.path.exists(dir_path):
                os.mkdir(dir_path)
            pdf_path = os.path.join(dir_path, f"{order_id}.pdf")
            c = canvas.Canvas(pdf_path, pagesize=letter)
            xx = 0
            yy = 0
            for i, item in enumerate(items):
                page = c
                self.write_label(page, item, order_id, i, len(items), xx, yy)
            c.save()
            context.logger.info("Label pdf generated successfully")
            s3_client = boto3.client("s3")
            bucket = "khawarbucket"
            key = f"{order_id}.pdf"
            with open(pdf_path, "rb") as f:
                s3_client.upload_fileobj(f, bucket, key)
            output["status"] = "success"
            output["url"] = f"https://{bucket}.s3.amazonaws.com/{key}"
            return json.dumps(output)
        except Exception as e:
            output["status"] = "error"
            output["url"] = ""
            context.logger.error(f"Error: {e}")
            return json.dumps(output)

    def download_file(self, bucket, file):
        try:
            s3_client = boto3.client("s3")
            obj = s3_client.get_object(Bucket=bucket, Key=file)
            return obj['Body'].read().decode('utf-8')
        except Exception as ex:
            logging.error(f"Error: {ex}")
        return ""

    def write_label(self, page, item, order_id, i, size, xx, yy):
        options = item.get("options")
        ny = 128
        for option in options:
            self.write_string(page, f"{option.get('name')}: {option.get('value')}", 12, xx + 10, yy + ny)
            ny += 20
        qr_img = self.create_qr(order_id, 145, 145)
        page.drawInlineImage(qr_img, xx + 190, yy + 15, width=145, height=145)
        bar_img = self.create_code_128(item.get("orderItemId"), 245, 45)
        page.drawInlineImage(bar_img, xx + 40, yy + 285, width=245, height=45)
        page.rect(xx, yy, 330, 330)
        page.rect(xx, yy + 330, 190, 80, stroke=1, fill=1)
        page.setStrokeColor(colors.black)
        page.setDash(3, 1)
        page.line(xx + 1, yy + 30, xx + 330, yy + 30)
        self.write_string(page, item.get("orderItemId"), 8, xx + 48, yy + 28)
        self.write_string(page, str(size), 18, xx + 50, yy + 305)
        self.write_string(page, f"{i + 1} - ", 18, xx + 25, yy + 305)

    def write_string(self, page, text, font_size, x, y):
        page.setFont("Helvetica", font_size)
        page.drawString(x, y, text)

    def create_qr(self, data, width, height):
        qr_img = encode(data)
        qr_img = qr_img.resize((width, height))
        buffered = BytesIO()
        qr_img.save(buffered, format="PNG")
        return buffered

    def create_code_128(self, data, width, height):
        bar_img = encode(data, encoding='code128', writer='image', output='raw')
        bar_img = Image.frombytes('L', (width, height), bar_img)
        buffered = BytesIO()
        bar_img.save(buffered, format="PNG")
        return buffered

def lambda_handler(event, context):
    handler = LambdaMethodHandler()
    return handler.handle_request(event, context)
