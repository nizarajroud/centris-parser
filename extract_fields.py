from bs4 import BeautifulSoup

fields = [
    "Building Type", "Occupancy", "Expected Delivery Date", "Deed of Sale Signature",
    "Building Size", "Lot Eval.", "Living Area", "Building Eval.", "Lot Size",
    "Mun. Taxes", "Lot Area", "School Taxes", "Cert. of Location",
    "Additional Rev.", "Body of Water", "Intergenerational", "Seasonal"
]

with open("11.html", "r", encoding="utf-8") as f:
    soup = BeautifulSoup(f, "html.parser")

for field in fields:
    label = soup.find("span", class_="d-textStrong d-fontSize--smallest", string=lambda s: s and field in s)
    if label:
        parent = label.find_parent("div", class_=lambda c: c and "col-sm-3" in c)
        if parent:
            next_div = parent.find_next_sibling("div", class_=lambda c: c and "col-sm-3" in c)
            if next_div:
                value = next_div.find("span", class_="d-fontSize--smallest")
                print(f"{field}: {value.get_text(strip=True) if value else 'N/A'}")
            else:
                print(f"{field}: N/A")
    else:
        print(f"{field}: N/A")
