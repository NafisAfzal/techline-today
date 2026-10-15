"""Authored Bangla examples for synthetic tests only; never a live translator."""
from pipeline.models import TranslationContent
from pipeline.translation import canonical_content

PHRASES = {
    "Significance has not been assessed from the collected evidence.": "সংগৃহীত প্রমাণ থেকে গুরুত্ব মূল্যায়ন করা হয়নি।",
    "Meridian releases an open multimodal model for local development": "নিজের কম্পিউটারে ব্যবহারের জন্য open multimodal model প্রকাশ করেছে Meridian",
    "Meridian publishes open weights for its multimodal model.": "Meridian তাদের multimodal model-এর weights সবার জন্য উন্মুক্ত করেছে।",
    "The model card lists a 128K context window.": "model card অনুযায়ী, context window হলো 128K।",
    "API access is limited to the developer preview.": "API শুধু developer preview-তে ব্যবহার করা যাবে।",
    "Harbor publishes a security patch for its developer gateway": "developer gateway-এর নিরাপত্তা সমস্যা ঠিক করতে patch প্রকাশ করেছে Harbor",
    "Harbor has released a security patch for the developer gateway.": "Harbor তাদের developer gateway-এর জন্য নিরাপত্তার patch প্রকাশ করেছে।",
    "The advisory identifies affected versions and an upgrade path.": "নিরাপত্তা বিজ্ঞপ্তিতে কোন version-গুলো আক্রান্ত এবং কীভাবে update করতে হবে, তা বলা আছে।",
    "Administrators should review the official advisory.": "সিস্টেমের দায়িত্বে থাকা ব্যক্তিদের মূল নিরাপত্তা বিজ্ঞপ্তিটি পড়া উচিত।",
    "A new retrieval paper publishes its evaluation dataset": "তথ্য খুঁজে বের করার পদ্ধতি নিয়ে নতুন গবেষণার পরীক্ষার dataset প্রকাশ",
    "The authors publish a retrieval evaluation dataset.": "তথ্য খুঁজে বের করার পদ্ধতি পরীক্ষা করতে গবেষকেরা একটি dataset প্রকাশ করেছেন।",
    "The preprint reports 24 evaluation tasks.": "প্রাথমিক গবেষণাপত্র অনুযায়ী, পরীক্ষায় 24টি কাজ রয়েছে।",
    "Results have not been independently reproduced.": "অন্য গবেষকেরা এখনও স্বাধীনভাবে ফলাফল পুনরায় পরীক্ষা করেননি।",
    "Atlas announces a developer accelerator with expanded memory": "বেশি memory-সহ developer accelerator-এর ঘোষণা দিয়েছে Atlas",
    "Atlas announces its developer accelerator.": "Atlas তাদের developer accelerator-এর ঘোষণা দিয়েছে।",
    "The specification lists 48GB of memory.": "প্রকাশিত specification অনুযায়ী, memory হলো 48GB।",
    "Independent performance measurements are not yet available.": "স্বাধীনভাবে করা performance পরীক্ষার ফল এখনও পাওয়া যায়নি।",
    "Cobalt offers a limited developer API credit for students": "শিক্ষার্থীদের জন্য সীমিত developer API credit দিচ্ছে Cobalt",
    "Cobalt offers a student developer credit.": "Cobalt শিক্ষার্থী developer-দের জন্য credit দিচ্ছে।",
    "Eligible applicants receive a $25 trial credit.": "শর্ত পূরণ করলে আবেদনকারীরা $25 trial credit পাবেন।",
    "The offer has an expiry date and requires student verification.": "এই সুবিধার মেয়াদ সীমিত। শিক্ষার্থী পরিচয় যাচাই করতে হবে।",
    "Check the source for what the model can do and who can use it.": "model কী করতে পারে এবং কারা ব্যবহার করতে পারবেন, তা জানতে মূল উৎসটি পড়ুন।",
    "Read the study's methods and limits before relying on its results.": "ফলাফলের ওপর নির্ভর করার আগে গবেষণার পদ্ধতি ও সীমাবদ্ধতা পড়ুন।",
    "Read the specifications and any independent tests before comparing hardware.": "hardware তুলনা করার আগে specification ও স্বাধীন পরীক্ষার ফল পড়ুন।",
    "Read the advisory to see whether your software is affected.": "আপনার software আক্রান্ত কি না, তা জানতে নিরাপত্তা বিজ্ঞপ্তিটি পড়ুন।",
    "Check eligibility, billing and expiry before using the offer.": "সুবিধাটি নেওয়ার আগে যোগ্যতার শর্ত, খরচ ও মেয়াদ দেখুন।",
    "Context": "ধারণক্ষমতা",
    "Memory": "মেমোরি",
    "Evaluation tasks": "পরীক্ষার কাজ",
    "Trial credit": "পরীক্ষামূলক credit",
    "Source-reported": "উৎসের তথ্য অনুযায়ী",
}


def translated_fixture(story):
    if story.headline not in PHRASES or not story.is_demo:
        return None
    canonical = canonical_content(story)
    translated = {}
    for key, value in canonical.items():
        if key == "broader_summary":
            translated[key] = " ".join(PHRASES[fact.text] for fact in story.key_facts[:5])
        elif isinstance(value, list):
            if any(text not in PHRASES for text in value):
                return None
            translated[key] = [PHRASES[text] for text in value]
        else:
            if value not in PHRASES:
                return None
            translated[key] = PHRASES[value]
    return TranslationContent.model_validate(translated)
