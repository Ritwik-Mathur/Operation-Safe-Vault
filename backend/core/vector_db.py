"""
Vector Database – ChromaDB + sentence-transformers
Stores known scam message embeddings for semantic similarity detection.
"""

import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict


KNOWN_SCAMS = [
    # ── Financial / Banking ───────────────────────────────────────
    "Congratulations! You have won a lottery. Click here to claim your prize now.",
    "Your bank account has been suspended. Verify your details immediately to restore access.",
    "URGENT: Your OTP is expiring. Share it now to keep your account active.",
    "You owe Rs 5000 in unpaid taxes. Pay immediately or face arrest.",
    "Dear customer, your KYC is incomplete. Update now or your account will be blocked within 24 hours.",
    "We need your credit card details to process your refund. Click the secure link below.",
    "Click this link to verify your PayTM/UPI account or it will be suspended permanently.",
    "Your SBI/HDFC/ICICI net banking password has expired. Click here to reset immediately.",

    # ── Government / Identity ─────────────────────────────────────
    "You have been selected for a government scheme. Send your Aadhaar and PAN to claim benefits.",
    "Your SIM card will be deactivated in 24 hours by TRAI order. Call us immediately.",
    "Income Tax Department: You have a pending refund of Rs 15,000. Click to claim now.",

    # ── Tech Support ──────────────────────────────────────────────
    "Hi, I'm from Microsoft support. Your computer has a virus. Give me remote access to fix it.",
    "Windows Defender alert: Your PC is infected. Call this number immediately for support.",
    "Your iCloud account has been compromised. Verify your Apple ID now.",

    # ── Package / Delivery ────────────────────────────────────────
    "Your parcel is held at customs. Pay Rs 2000 processing fee to release it.",
    "Amazon delivery failed. Update your address and pay redelivery fee.",

    # ── Prize / Reward ────────────────────────────────────────────
    "Win an iPhone 15! You are our lucky draw winner. Click the link to claim your prize.",
    "Investment opportunity: 40% returns guaranteed in 30 days. Limited slots available.",

    # ── Social Engineering ────────────────────────────────────────
    "Send money urgently, I am stuck abroad and lost my wallet. Will repay tomorrow.",
    "Hi Mom/Dad, I dropped my phone in water. This is my new number. Can you send me Rs 5000?",

    # ── Job / Loan ────────────────────────────────────────────────
    "Work from home and earn Rs 50,000 per day. No experience needed. WhatsApp us now.",
    "Your loan of Rs 5,00,000 has been pre-approved. Pay Rs 2,000 processing fee to activate.",

    # ── AI-Generated Phishing (modern) ────────────────────────────
    "As per our records, your account shows suspicious activity. To prevent unauthorized access, please verify your identity by clicking the secure link below. This is an automated security measure.",
    "Dear valued customer, we have detected a login attempt from an unrecognized device. If this was not you, please immediately verify your account to prevent any unauthorized transactions.",

    # ── Voice Call Transcripts — Banking Impersonation ────────────
    "Hello, I am calling from the fraud department of your bank. We have detected an unauthorized transaction of Rs 45,000 on your account. To stop this transaction, I need you to share your OTP right now.",
    "Sir, this is an urgent call from SBI customer care. Your account has been flagged for suspicious activity. Please provide your debit card number and CVV so we can verify your identity and secure your account.",
    "Madam, I am calling from HDFC bank. Your net banking has been temporarily blocked due to multiple failed login attempts. To unlock it immediately, please share the OTP we just sent to your registered mobile number.",
    "This is a call from the RBI cyber fraud helpline. We have identified that your account is being misused. You need to transfer your funds to a secure government account immediately. I will guide you through the process.",
    "Hello, your credit card ending in 4567 has been used for a transaction of Rs 12,000 at an unknown merchant. If you did not authorize this, press 1 and share your card details to block it immediately.",

    # ── Voice Call Transcripts — Government Impersonation ─────────
    "I am calling from the Income Tax Department of India. Our records show you have tax dues of Rs 80,000. If you do not pay within the next two hours, a warrant will be issued for your arrest. Call back immediately on this number.",
    "This is the Narcotics Control Bureau. Your Aadhaar number has been linked to illegal drug shipments. You are under digital arrest. Do not leave your home and do not speak to anyone until our officer arrives.",
    "Hello, I am Officer Singh from the CBI cyber crime branch. We have found your bank account is being used for money laundering. To cooperate with our investigation, transfer your savings to this safe account number we provide.",
    "This call is from TRAI, the Telecom Regulatory Authority. We have received complaints against your mobile number for sending fraudulent messages. Your number will be disconnected in two hours unless you verify your Aadhaar details.",
    "I am calling from the customs department. A parcel in your name containing foreign currency and drugs has been seized at the airport. To avoid arrest, you must pay a clearance fine of Rs 25,000 immediately.",

    # ── Voice Call Transcripts — Tech Support Scam ────────────────
    "Hello, I am calling from Microsoft Windows support team. Our system has detected that your computer is sending error reports and is infected with a dangerous virus. Please allow me remote access using TeamViewer so I can fix it for free.",
    "This is an automated alert from Apple. Your iCloud account has been compromised and someone is trying to steal your photos and data. Press 1 to speak with an Apple certified technician immediately.",
    "Hi, I am calling from your internet service provider. We have detected unusual activity from your IP address indicating your router has been hacked. I need to remotely access your computer to fix this security breach.",

    # ── Voice Call Transcripts — KYC / UPI Scam ──────────────────
    "Hello, I am calling from Google Pay support. Your UPI ID has been flagged and will be deactivated in 24 hours if you do not complete your KYC verification. Please share your Aadhaar number and the OTP you receive.",
    "This is PhonePe customer support. We are upgrading all accounts and your KYC documents are outdated. To continue using our service, please share your PAN card number and bank account details for re-verification.",
    "I am calling from Paytm. Your wallet has crossed the KYC limit. To continue transacting, share your Aadhaar OTP for instant verification. This is mandatory as per RBI guidelines.",

    # ── Voice Call Transcripts — Loan / Job Scam ──────────────────
    "Congratulations! You have been pre-approved for an instant personal loan of Rs 5 lakhs at just 1% interest. To process your loan within 30 minutes, pay a refundable processing fee of Rs 3,000 to our account.",
    "Hello, we are hiring work from home employees. You can earn Rs 800 per hour just by liking videos and completing simple tasks. To register, pay a one-time registration fee of Rs 1,500.",

    # ── Voice Call Transcripts — Hindi / Hinglish ─────────────────
    "Namaste, main aapke bank ki fraud prevention team se bol raha hoon. Aapke account mein ek suspicious transaction detect hui hai. Aapka account block hone se bachane ke liye abhi apna OTP share karein.",
    "Bhai sahab, main CBI officer bol raha hoon. Aapke naam pe ek illegal parcel pakda gaya hai. Agar arrest nahi chahte toh abhi is number pe Rs 50,000 transfer karein aur kisi ko mat batana.",
    "Madam ji, aapka SIM card agle 2 ghante mein band ho jayega. TRAI ka notice hai. Aadhaar card number aur OTP share karein turant warna number permanently block ho jayega.",
    "Hello sir, main Amazon delivery agent bol raha hoon. Aapka parcel customs mein atak gaya hai. Sirf Rs 1,500 ka customs duty bharna hoga. UPI pe bhej dijiye abhi.",
    "Aapne lucky draw jeeta hai. Ek crore rupaye aur ek car aapki prize hai. Claim karne ke liye apna bank account number aur Aadhaar details abhi WhatsApp karein is number pe.",

    # ── Devanagari Script Scam Templates ─────────────────────────
    "नमस्ते, मैं आपके बैंक की फ्रॉड टीम से बोल रहा हूं। आपके खाते में संदिग्ध लेनदेन हुआ है। खाता बंद होने से बचाने के लिए अभी अपना ओटीपी शेयर करें।",
    "आपका सिम कार्ड अगले 2 घंटे में बंद हो जाएगा। ट्राई का नोटिस है। आधार नंबर और ओटीपी तुरंत शेयर करें वरना नंबर परमानेंट ब्लॉक हो जाएगा।",
    "मैं सीबीआई अधिकारी बोल रहा हूं। आपके नाम पर अवैध पार्सल पकड़ा गया है। गिरफ्तारी से बचने के लिए अभी ₹50,000 ट्रांसफर करें और किसी को मत बताना।",
    "आयकर विभाग से सूचना है। आपके खाते में कर बकाया है। दो घंटे में भुगतान न करने पर गिरफ्तारी वारंट जारी होगा। अभी इस नंबर पर कॉल करें।",
    "बधाई हो! आपने लकी ड्रा में एक करोड़ रुपये और एक कार जीती है। क्लेम करने के लिए अपना आधार नंबर और बैंक खाता विवरण व्हाट्सएप करें।",
    "आपका केवाईसी अपूर्ण है। 24 घंटे में अपडेट न करने पर आपका खाता ब्लॉक हो जाएगा। अभी आधार नंबर और ओटीपी शेयर करें।",
    "मैं डिजिटल अरेस्ट की सूचना दे रहा हूं। आपका आधार नंबर मनी लॉन्ड्रिंग केस में लिंक पाया गया है। घर से बाहर मत जाइए और किसी को मत बताइए।",
    "गूगल पे सपोर्ट से बोल रहा हूं। आपका यूपीआई आईडी 24 घंटे में बंद हो जाएगा। केवाईसी के लिए आधार नंबर और ओटीपी अभी शेयर करें।",

    # ── Voice Cloning — Family Emergency Impersonation ────────────
    "Mom it's me, I'm calling from a new number, I dropped my phone in water. I had a car accident and I'm at the police station. I need Rs 50,000 for bail right now. Please don't tell Dad yet, just transfer the money first.",
    "Dad this is your son. Please don't panic. I got into some trouble and I'm at the police station. My phone broke so I'm calling from a friend's number. I need bail money urgently, please send Rs 30,000 right now and don't tell anyone.",
    "Beta main bol raha hoon, mera phone kho gaya isliye naye number se call kar raha hoon. Main hospital mein hoon, accident ho gaya tha. Turant Rs 40,000 ki zaroorat hai operation ke liye. Kisi ko mat batana abhi.",
    "Mummy main hoon, please ghabrana mat. Main police station pe hoon, kuch gadbad ho gayi. Bail ke liye paisa chahiye abhi. Ye number yaad kar lo mera naya number hai. 20,000 bhej do turant please kisi ko mat batana.",
    "Hello aunty, main aapka beta bol raha hoon. Naye number se call kar raha hoon. Main bahut badi musibat mein hoon. Mujhe abhi 50,000 rupaye chahiye. Please UPI pe transfer kar do aur ghar mein kisi ko mat batana main baad mein explain karunga.",
    "This is your daughter calling from a colleague's phone. My phone got stolen. I'm stranded and I need money urgently for an emergency. Please transfer Rs 25,000 to this account right now. I'll explain everything later just please hurry.",
]


class VectorDB:
    def __init__(self, persist_dir: str = "./chroma_db"):
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2",
            device="cpu",
        )
        import os
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
        os.environ.setdefault("HF_DATASETS_OFFLINE", "1")
        self.collection = self.client.get_or_create_collection(
            name="scam_templates",
            embedding_function=self.ef,
        )

    def seed_known_scams(self):
        """Populate DB with known scam templates if empty or outdated."""
        if self.collection.count() >= len(KNOWN_SCAMS):
            return
        self.collection.upsert(
            documents=KNOWN_SCAMS,
            ids=[f"scam_{i}" for i in range(len(KNOWN_SCAMS))],
            metadatas=[{"type": "known_scam", "index": i} for i in range(len(KNOWN_SCAMS))],
        )

    def query_similarity(self, text: str, n_results: int = 3) -> List[Dict]:
        """Return top-N similar scam templates with similarity percentage."""
        count = self.collection.count()
        if count == 0:
            return []
        results = self.collection.query(
            query_texts=[text],
            n_results=min(n_results, count),
        )
        output = []
        if results and results["documents"]:
            for doc, dist in zip(results["documents"][0], results["distances"][0]):
                similarity = round((1 - dist / 2) * 100, 1)
                output.append({"template": doc, "similarity_pct": similarity})
        return output

    def add_scam(self, text: str, reported_by: str = "user"):
        """Add a user-reported scam to the database (human-in-the-loop learning)."""
        doc_id = f"user_reported_{self.collection.count()}"
        self.collection.add(
            documents=[text],
            ids=[doc_id],
            metadatas=[{"type": "user_reported", "reported_by": reported_by}],
        )
