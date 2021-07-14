import yake
text = """i hate the other account because it has no nitro lmfao"""
custom_kw_extractor = yake.KeywordExtractor(lan= "en", n=3, dedupLim=0.9, features=None)
keywords = custom_kw_extractor.extract_keywords(text)
for kw in keywords:
    print(kw)