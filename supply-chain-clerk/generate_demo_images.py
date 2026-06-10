import os
import random
from PIL import Image, ImageDraw, ImageFont

output_dir = "demo_documents"
os.makedirs(output_dir, exist_ok=True)

products = {
    "herbal": [
        "Ashwagandha Extract", "Ginseng Root", "Turmeric Powder", 
        "Aloe Vera Gel", "Neem Leaves", "Tulsi Drops", "Brahmi Vati"
    ],
    "analgesic": [
        "Paracetamol 500mg", "Ibuprofen 400mg", "Aspirin 75mg", 
        "Diclofenac Gel", "Naproxen 250mg", "Ketorolac", "Acetaminophen"
    ],
    "supplement": [
        "Vitamin C 1000mg", "Calcium + D3", "Omega-3 Fish Oil", 
        "Multivitamin Gummies", "Iron Tablets", "Magnesium Citrate", "Zinc 50mg"
    ]
}

suppliers = ["Himalaya Herbs", "PharmaCorp", "VitaLife", "Medix", "Nature Bounty"]

def generate_invoice(index, category, product):
    batch = f"BT-2024-{random.randint(100, 999)}"
    expiry = f"202{random.randint(5, 8)}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}"
    supplier = random.choice(suppliers)
    qty = random.randint(10, 500)
    uom = random.choice(["units", "bottles", "packs", "boxes"])
    
    text = (
        "INVOICE\n\n"
        f"Batch: {batch}\n"
        f"Expiry: {expiry}\n"
        f"Supplier: {supplier}\n"
        f"Product: {product}\n"
        f"Qty: {qty} {uom}"
    )
    
    # Create a small image, draw text, and upscale so it's readable without custom fonts
    small_img = Image.new('RGB', (250, 150), color='white')
    d = ImageDraw.Draw(small_img)
    
    try:
        font = ImageFont.load_default(size=12)
    except TypeError:
        font = ImageFont.load_default()
        
    d.text((15, 15), text, fill="black", font=font)
    
    # Upscale
    img = small_img.resize((1000, 600), Image.NEAREST)
    
    filename = f"{index:02d}_{category}_{product.replace(' ', '_')}.jpg"
    filepath = os.path.join(output_dir, filename)
    img.save(filepath, quality=95)
    print(f"Generated {filepath}")

# Generate 20 images
count = 1
for category, prod_list in products.items():
    for prod in prod_list:
        if count > 20: break
        generate_invoice(count, category, prod)
        count += 1
