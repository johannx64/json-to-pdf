import json
import io
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, Paragraph, Image
from reportlab.platypus import Image
from PIL import Image as PILImage
from pylibdmtx.pylibdmtx import encode as dmtx_encode
from pylibdmtx.pylibdmtx import decode as dmtx_decode
from barcode import get_barcode
from barcode.writer import ImageWriter

class ShipmentStickerTemplate(BaseDocTemplate):
    def __init__(self, filename, **kwargs):
        super().__init__(filename, **kwargs)
        
        # Define margins and frames for the page
        self.left_margin = 36
        self.right_margin = 36
        self.top_margin = 36
        self.bottom_margin = 36
        
        # Define a main frame for the content
        main_frame = Frame(
            self.left_margin, self.bottom_margin, 
            self.width - self.left_margin - self.right_margin, 
            self.height - self.top_margin - self.bottom_margin
        )
        
        # Create a page template with the main frame
        main_template = PageTemplate(id='main', frames=[main_frame])
        
        # Add the page template to the document
        self.addPageTemplates(main_template)

def handle_json_request(json_data):
    output = {}
    try:
        order_id = json_data.get('orderId')
        order_key = json_data.get('orderKey')
        custom_field2 = json_data.get('customField2')
        custom_field3 = json_data.get('customField3')
        
        item = json_data.get('item')
        item_number = json_data.get('itemNumber')
        item_total = json_data.get('itemTotal')
        
        buffer = io.BytesIO()
        doc = ShipmentStickerTemplate(buffer, pagesize=letter)
        elements = []
        
        styles = getSampleStyleSheet()
        title_style = styles['Title']
        header_style = ParagraphStyle(
            name='HeaderStyle',
            parent=styles['Heading1'],
            fontSize=14,
            leading=16
        )
        bold_italic_style = ParagraphStyle(
            name='BoldItalicStyle',
            parent=styles['Normal'],
            fontSize=10,
            leading=12,
            textColor='black',
            fontName='Helvetica-BoldOblique'
        )
        bold_italic_style.spaceAfter = 5
        
        elements.append(Paragraph(f"Item {item_number} of {item_total}", title_style))
        elements.append(Paragraph(f"{custom_field3}", header_style))
        
        data_matrix_img = generate_data_matrix(order_id, 30, 30)
        elements.append(data_matrix_img)
        
        #elements.append(Spacer(1, 12))
        
        elements.append(Paragraph(f"Order #: {order_key}", styles['Normal']))
        elements.append(Paragraph(f"Item #: {item.get('lineItemKey')}", styles['Normal']))
        elements.append(Paragraph(f"SKU #: {item.get('sku')}", styles['Normal']))
        elements.append(Paragraph(f"QTY #: {item.get('quantity')}", bold_italic_style))
        elements.append(Paragraph(f"{custom_field2}", styles['Normal']))
        
        barcode_img = generate_barcode(order_id, 'code128', 200, 50)
        elements.append(barcode_img)
        
        doc.build(elements)
        buffer.seek(0)
        pdf_data = buffer.getvalue()
        
        with open(f"{order_id}.pdf", 'wb') as f:
            f.write(pdf_data)
        
        output['status'] = 'success'
        output['url'] = f"{order_id}.pdf"
        
        return output
    except Exception as e:
        output['status'] = 'error'
        output['url'] = ''
        print(f"Error: {str(e)}")
        return output

def generate_data_matrix(data, width, height):
    encoded = dmtx_encode(data.encode('utf8'))
    img = PILImage.frombytes('RGB', (encoded.width, encoded.height), encoded.pixels)
    img = img.resize((width, height), resample=PILImage.LANCZOS)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return Image(buffer, width=width, height=height)

def generate_barcode(data, code_type, width, height):
    barcode_writer = ImageWriter()
    barcode = get_barcode(code_type, data, barcode_writer)
    barcode_image = barcode.render()
    barcode_bytes = io.BytesIO()
    barcode_image.save(barcode_bytes, format="PNG")
    barcode_bytes.seek(0)
    barcode_pil_image = PILImage.open(barcode_bytes)
    barcode_pil_image = barcode_pil_image.resize((width, height), resample=PILImage.LANCZOS)
    buffer = io.BytesIO()
    barcode_pil_image.save(buffer, format="PNG")
    buffer.seek(0)
    return Image(buffer, width=width, height=height)

# Sample JSON input data
input_data = {
    "orderId": "49379385",
    "orderKey": "1c2f4882b9c04e59b41eb03e27ba2dce",
    "orderDate": "2024-01-02T11:35:28.0000000",
    "customField2": "RDJ-101",
    "customField3": "OF",
    "storeId": 285146,
    "itemNumber": 1,
    "itemTotal": 2,
    "item": {
        "orderItemId": 91566945,
        "lineItemKey": "105",
        "sku": "ABC-3",
        "name": "gold ring",
        "imageUrl": None,
        "weight": None,
        "quantity": 1,
        "unitPrice": 0,
        "taxAmount": None,
        "shippingAmount": None,
        "warehouseLocation": None,
        "options": [
            {
                "name": "lat",
                "value": "34.052235"
            },
            {
                "name": "long",
                "value": "-118.243683"
            },
            {
                "name": "chain-type",
                "value": "rolo"
            },
            {
                "name": "chain-length",
                "value": "18 inches"
            },
            {
                "name": "finish",
                "value": "14k yellow gold plated"
            },
            {
                "name": "birthstone",
                "value": "peridot"
            },
            {
                "name": "diamond-bezel",
                "value": "none"
            },
            {
                "name": "finish",
                "value": "14k yellow gold plated"
            },
            {
                "name": "gift wrap",
                "value": "none"
            }
        ],
        "productId": 7425301,
        "fulfillmentSku": None,
        "adjustment": False,
        "upc": None,
        "createDate": "2024-02-13T15:25:34.993",
        "modifyDate": "2024-02-13T15:25:34.993"
    }
}

# Call the function with the sample input data
result = handle_json_request(input_data)
print(result)
