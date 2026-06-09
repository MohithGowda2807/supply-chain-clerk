import os
import random
import spacy
from spacy.training.example import Example
from spacy.util import minibatch, compounding

print("Generating synthetic training data for Custom OCR-NER model...")

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
uoms = ["units", "bottles", "packs", "boxes"]

TRAIN_DATA = []

# Generate 2000 examples for robust training
for _ in range(2000):
    batch = f"BT-202{random.randint(2,6)}-{random.randint(100, 999)}"
    expiry = f"202{random.randint(5, 8)}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}"
    supplier = random.choice(suppliers)
    category = random.choice(list(products.keys()))
    product = random.choice(products[category])
    qty = str(random.randint(10, 500))
    uom = random.choice(uoms)
    
    # Add variation to templates to mimic OCR mistakes and variations
    # We will build the text piece by piece to keep exact track of indices
    
    parts = []
    
    # Randomly choose a structure
    structure = random.choice([1, 2, 3])
    
    if structure == 1:
        p1 = "INVOICE\nBatch: "; parts.append((p1, None))
        p2 = batch; parts.append((p2, "batch_no"))
        p3 = "\nExpiry: "; parts.append((p3, None))
        p4 = expiry; parts.append((p4, "expiry_date"))
        p5 = "\nSupplier: "; parts.append((p5, None))
        p6 = supplier; parts.append((p6, "supplier_name"))
        p7 = "\nProduct: "; parts.append((p7, None))
        p8 = product; parts.append((p8, "product_name"))
        p9 = "\nQty: "; parts.append((p9, None))
        p10 = qty; parts.append((p10, "quantity"))
        p11 = " "; parts.append((p11, None))
        p12 = uom; parts.append((p12, "unit_of_measure"))
    elif structure == 2:
        p1 = "INVOICE NO: 1234\nBATCH: "; parts.append((p1, None))
        p2 = batch; parts.append((p2, "batch_no"))
        p3 = "\nEXP: "; parts.append((p3, None))
        p4 = expiry; parts.append((p4, "expiry_date"))
        p5 = "\nVENDOR: "; parts.append((p5, None))
        p6 = supplier; parts.append((p6, "supplier_name"))
        p7 = "\nITEM: "; parts.append((p7, None))
        p8 = product; parts.append((p8, "product_name"))
        p9 = "\nQUANTITY: "; parts.append((p9, None))
        p10 = qty; parts.append((p10, "quantity"))
        p11 = " "; parts.append((p11, None))
        p12 = uom; parts.append((p12, "unit_of_measure"))
    else:
        p1 = "Batch No: "; parts.append((p1, None))
        p2 = batch; parts.append((p2, "batch_no"))
        p3 = " | Exp: "; parts.append((p3, None))
        p4 = expiry; parts.append((p4, "expiry_date"))
        p5 = " | Supplier: "; parts.append((p5, None))
        p6 = supplier; parts.append((p6, "supplier_name"))
        p7 = "\n"; parts.append((p7, None))
        p8 = product; parts.append((p8, "product_name"))
        p9 = " - "; parts.append((p9, None))
        p10 = qty; parts.append((p10, "quantity"))
        p11 = " "; parts.append((p11, None))
        p12 = uom; parts.append((p12, "unit_of_measure"))

    text = ""
    entities = []
    current_idx = 0
    
    for content, label in parts:
        if label:
            entities.append((current_idx, current_idx + len(content), label))
        text += content
        current_idx += len(content)
    
    TRAIN_DATA.append((text, {"entities": entities}))

print(f"Generated {len(TRAIN_DATA)} training examples.")

def train_spacy(train_data, iterations=30):
    nlp = spacy.blank("en")
    
    if "ner" not in nlp.pipe_names:
        ner = nlp.add_pipe("ner", last=True)
    else:
        ner = nlp.get_pipe("ner")
        
    for _, annotations in train_data:
        for ent in annotations.get("entities"):
            ner.add_label(ent[2])
            
    other_pipes = [pipe for pipe in nlp.pipe_names if pipe != "ner"]
    with nlp.disable_pipes(*other_pipes):
        optimizer = nlp.begin_training()
        
        for itn in range(iterations):
            random.shuffle(train_data)
            losses = {}
            
            batches = minibatch(train_data, size=compounding(4.0, 32.0, 1.001))
            for batch in batches:
                examples = []
                for text, annotations in batch:
                    doc = nlp.make_doc(text)
                    example = Example.from_dict(doc, annotations)
                    examples.append(example)
                    
                nlp.update(
                    examples,
                    drop=0.35,  # Dropout parameter
                    sgd=optimizer,
                    losses=losses,
                )
            print(f"Iteration {itn + 1}/{iterations} - Losses: {losses}")
            
    return nlp

print("Starting custom AI model training (this uses optimized hyperparameters)...")
trained_nlp = train_spacy(TRAIN_DATA, iterations=30)
model_dir = "invoice_ner_model"
trained_nlp.to_disk(model_dir)
print(f"Model saved to {model_dir}")
