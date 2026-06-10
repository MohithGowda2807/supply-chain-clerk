import joblib
import random
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import train_test_split

print("Initializing ML Text Classifier Training...")

# 1. Define the Base Dataset
DATA = {
    "herbal": [
        "Ashwagandha Extract", "Turmeric Root", "Tulsi Drops", "Neem Capsules", 
        "Aloe Vera Gel", "Ginseng Complex", "Echinacea Extract", "Brahmi Vati", 
        "Triphala Churna", "Giloy Tablets", "Amla Juice", "Shatavari Powder",
        "Herbal Cough Syrup", "Moringa Extract", "Gotu Kola"
    ],
    "analgesic": [
        "Paracetamol 500mg", "Ibuprofen 400mg", "Aspirin 75mg", "Diclofenac Gel", 
        "Naproxen 250mg", "Acetaminophen", "Ketorolac", "Tramadol", "Celecoxib",
        "Pain Relief Spray", "Meloxicam", "Indomethacin", "Piroxicam",
        "Codeine Phosphate", "Mefenamic Acid"
    ],
    "supplement": [
        "Vitamin C 1000mg", "Omega-3 Fish Oil", "Multivitamin Complex", 
        "Iron Tablets", "Calcium + D3", "Zinc Citrate", "Magnesium Glycinate",
        "B-Complex Softgels", "Folic Acid", "Vitamin B12", "Protein Powder",
        "Collagen Peptides", "Probiotic 50 Billion", "Glucosamine Chondroitin",
        "Melatonin 5mg"
    ]
}

# 2. Augment Data with OCR Typos
def introduce_ocr_typos(text, num_typos=1):
    typos = []
    substitutions = {'i': 'l', 'l': 'i', '0': 'o', 'o': '0', 'e': 'c', 'c': 'e', 'm': 'rn', 'rn': 'm', 'f': 't', 't': 'f', 'b': 'h', 'h': 'b'}
    for _ in range(num_typos):
        chars = list(text.lower())
        if len(chars) > 3:
            # Random substitution
            for _ in range(random.randint(1, 2)):
                idx = random.randint(0, len(chars)-1)
                char = chars[idx]
                if char in substitutions:
                    chars[idx] = substitutions[char]
                elif char.isalpha():
                    chars[idx] = random.choice('abcdefghijklmnopqrstuvwxyz')
        typos.append("".join(chars).title())
    return typos

X_raw = []
y_raw = []

for category, items in DATA.items():
    for item in items:
        # Add original
        X_raw.append(item)
        y_raw.append(category)
        
        # Add 10 varied OCR typos for robust training
        for _ in range(10):
            typo_list = introduce_ocr_typos(item)
            for typo in typo_list:
                X_raw.append(typo)
                y_raw.append(category)

        # Add partial names
        parts = item.split()
        if len(parts) > 1:
            X_raw.append(parts[0])
            y_raw.append(category)

print(f"Generated dataset with {len(X_raw)} training samples.")

# 3. Build ML Pipeline
# Character n-grams are incredibly robust against OCR typos!
pipeline = make_pipeline(
    TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5), lowercase=True),
    LinearSVC(C=1.0, dual="auto")
)

# 4. Train Model
print("Training Support Vector Classifier...")
X_train, X_test, y_train, y_test = train_test_split(X_raw, y_raw, test_size=0.1, random_state=42)
pipeline.fit(X_train, y_train)

score = pipeline.score(X_test, y_test)
print(f"Model Accuracy on Test Set: {score*100:.2f}%")

# 5. Save Model
model_path = Path(__file__).parent / "product_classifier.joblib"
joblib.dump(pipeline, model_path)
print(f"Model saved successfully to {model_path}")

# Test with user's specific OCR typos
test_cases = ["Iron Tablets", "Ibuproten", "Cmega-3"]
print("\nTesting specific edge cases:")
for tc in test_cases:
    pred = pipeline.predict([tc])[0]
    print(f"   '{tc}' -> routed to [{pred.upper()}]")
