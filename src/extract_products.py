import glob
import json
from collections import defaultdict


def extract_all_products(output_file="products.json"):
    try:
        products = defaultdict(list)
        existing_items = set()

        # Process all search result files
        for result_file in glob.glob("search_results_*.json"):
            keyword = result_file.replace("search_results_", "").replace(".json", "")

            with open(result_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            if (
                "data" in data
                and "b2c" in data["data"]
                and "onSaleList" in data["data"]["b2c"]
            ):

                for item in data["data"]["b2c"]["onSaleList"]:
                    product = {
                        "item": item["goodsName"],
                        "price": item["memberPrice"] / 100,
                    }

                    item_key = f"{product['item']}_{product['price']}"
                    if item_key not in existing_items:
                        products[keyword].append(product)
                        existing_items.add(item_key)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(products, f, ensure_ascii=False, indent=2)

        print(f"Successfully extracted products for {len(products)} keywords")

    except Exception as e:
        print(f"Error processing products: {str(e)}")


if __name__ == "__main__":
    extract_all_products()
