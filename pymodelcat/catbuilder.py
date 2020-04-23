import pandas as pd
from sciencebasepy import SbSession
import requests
import json
import extruct
from w3lib.html import get_base_url
from bs4 import BeautifulSoup


class Catbuilder:
    def __init__(self, username=None):
        self.default_catalog_id = '5e8de96182cee42d134687cc'
        self.meta_bucket_list = [
            "all",
            "json_response",
            "microdata",
            "json-ld",
            "opengraph",
            "microformat",
            "rdfa",
            "meta_content"
        ]

        if username is not None:
            self.sb = SbSession().loginc(username)
        else:
            self.sb = SbSession()

    def create_model_catalog(self, parent_id=None, title="USGS Model Catalog", body=None, delete_if_exists=True):
        if parent_id is None:
            parent_id = self.sb.get_my_items_id()

        if delete_if_exists:
            existing_items = json.loads(self.sb.get(
                f"https://www.sciencebase.gov/catalog/items?format=json&parentId={parent_id}&lq=title:{title}"
            ))

            if existing_items["total"] > 0:
                for item in existing_items["items"]:
                    if item["hasChildren"]:
                        sb.delete_items(sb.get_child_ids(item["id"]))
                    sb.delete_item(item)

        model_catalog_item = {
            'title': title,
            'parentId': parent_id
        }

        if body is not None:
            model_catalog_item["body"] = body

        return self.sb.create_item(model_catalog_item)

    def get_models(self, model_catalog_id=None):
        if model_catalog_id is None:
            model_catalog_id = self.default_catalog_id

        models = list()
        links = list()
        items = self.sb.find_items({'parentId': model_catalog_id, 'fields': 'title,webLinks', 'max': 100})
        while items and 'items' in items:
            for item in items['items']:
                del item["link"]
                del item["relatedItems"]
                models.append(item)
                links.extend([l["uri"] for l in item["webLinks"]])
            items = self.sb.next(items)

        unique_links = list(set(links))

        return models, unique_links

    def load_models_spreadsheet(self, file_path="USGS_models_named_models.xlsx"):
        output_link_columns = ["Output", "Output.1", "Output.2", "Output.3", "Output.4"]

        usgs_models = pd.read_excel(file_path)

        # Replace NaN with None (makes it simpler to evaluate values)
        usgs_models = usgs_models.replace({pd.np.nan: None})

        # Put all of the output links into a list (makes it easier to process these later)
        usgs_models["output_links"] = usgs_models[output_link_columns].values.tolist()
        usgs_models = usgs_models.drop(columns=output_link_columns)

        # Drop any unnamed columns (blanks in the Excel file)
        usgs_models = usgs_models.drop(columns=[i for i in list(usgs_models.columns) if i.find("Unnamed") != -1])

        return usgs_models

    def sb_party_to_contact(self, search_term):
        search_result = requests.get(
            f"https://www.sciencebase.gov/directory/people?q={search_term}&format=json&dataset=all&max=10"
        ).json()

        if search_result["total"] == 1:
            person_record = search_result["people"][0]

            sb_contact = {
                "name": person_record["displayName"],
                "type": "Contact",
                "oldPartyId": person_record["id"],
                "contactType": person_record["type"],
                "onlineResource": f"https://my.usgs.gov/catalog/Global/catalogParty/show/{person_record['id']}",
                "email": person_record["email"],
                "active": person_record["active"],
                "jobTitle": person_record["extensions"]["personExtension"]["jobTitle"],
                "firstName": person_record["extensions"]["personExtension"]["firstName"],
                "lastName": person_record["extensions"]["personExtension"]["lastName"]
            }

            if "orcId" in person_record.keys():
                sb_contact["orcId"] = person_record["orcId"]

        else:
            sb_contact = {
                "name": search_term,
                "type": "Contact",
                "email": search_term
            }

        return sb_contact

    def sb_web_link(self, url, title="Model Reference Link"):
        return {
            "type": "webLink",
            "typeLabel": "Web Link",
            "uri": url,
            "rel": "related",
            "title": title,
            "hidden": False
        }

    def build_model_documents(self, df_models=None):
        if df_models is None:
            df_models = self.load_models_spreadsheet()

        model_documents = list()

        for index, record in df_models.iterrows():
            new_model_item = {
                "parentId": model_catalog["id"],
                "title": record["Model Name"],
                "webLinks": list()
            }

            # Here we take the contact email addresses and use the sb_party_to_contact function
            # to look them up and make proper contacts for ScienceBase
            record_contacts = record["Contact(s)"].split(";")
            if len(record_contacts) > 0:
                new_model_item["contacts"] = [self.sb_party_to_contact(contact) for contact in record_contacts]

            # Here we split the sometimes lists of model reference links and add them to web links
            for link in record["Link"].split(";"):
                new_model_item["webLinks"].append(self.sb_web_link(link))

            # Here we filter down to just output link values not already processed as a
            # model reference and containing an actual value
            for link in [l for l in record["output_links"] if
                         l is not None and len(l.strip()) > 0 and not l in [i["uri"] for i in
                                                                            new_model_item["webLinks"]]]:
                new_model_item["webLinks"].append(self.sb_web_link(link, "Model Output Data"))

            model_documents.append(new_model_item)

        return model_documents

    def model_catalog_list_out(
            self,
            model_catalog_id,
            include_contact=True,
            include_ref_link=True,
            include_sb_link=True,
            return_data=None,
            write_to_excel=True,
            file_name="usgs_model_catalog.xlsx"
    ):
        simple_model_list = list()
        column_list = ["Model Name"]
        if include_contact:
            column_list.append("Contact")

        if include_ref_link:
            column_list.append("Model Reference Link")

        if include_sb_link:
            column_list.append("ScienceBase Link")

        items = self.sb.find_items({"parentId": model_catalog_id, "fields": "title,webLinks,contacts"})
        while items and 'items' in items:
            for item in items['items']:
                simple_item = {
                    "Model Name": item['title']
                }

                if include_contact:
                    simple_item["Contact"] = next((c["name"] for c in item["contacts"]), None)

                if include_ref_link:
                    simple_item["Model Reference Link"] = next(
                        (l["uri"] for l in item["webLinks"] if l["title"] == "Model Reference Link"), None)

                if include_sb_link:
                    simple_item["ScienceBase Link"] = item["link"]["url"]

                simple_model_list.append(simple_item)

            items = self.sb.next(items)

        df_model_list = pd.DataFrame(simple_model_list)

        if write_to_excel:
            df_model_list.to_excel(file_name, index=False, columns=column_list)

        if return_data == "dataframe":
            return df_model_list

        if return_data == "dict":
            return simple_model_list

    def gather_model_meta(self, link):
        eval_result = {
            "url": link
        }

        try:
            r = requests.get(link, headers={"Accept": "application/json"})
        except Exception as e:
            eval_result["error_condition"] = e
            return eval_result

        try:
            eval_result["json_response"] = r.json()
        except Exception as e:
            eval_result["json_response"] = None

        try:
            eval_result["structured_data"] = extruct.extract(r.text, base_url=get_base_url(r.text, r.url))
        except Exception as e:
            eval_result["structured_data"] = None

        eval_result["meta_content"] = self.meta_scraper(r.text)

        return eval_result

    def meta_scraper(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        meta_content = dict()

        if soup.title is not None:
            meta_content["title"] = soup.title.string

        for meta in soup.findAll("meta"):
            metaname = meta.get('name', '')
            try:
                metacontent = meta["content"].strip()
            except:
                metacontent = None
            if isinstance(metaname, str) and isinstance(metacontent, str) and len(metacontent) > 0:
                meta_content[metaname] = metacontent

        return meta_content

    def subset_model_meta(self, result_list, bucket="all"):
        if bucket == "all":
            subset = result_list

        if bucket == "json_response":
            subset = [i for i in result_list if "json_response" in i.keys() and i["json_response"] is not None]

        if bucket == "microdata":
            subset = [i for i in result_list if "structured_data" in i.keys() and i["structured_data"] is not None and len(
                i["structured_data"]["microdata"]) > 0]

        if bucket == "json-ld":
            subset = [i for i in result_list if "structured_data" in i.keys() and i["structured_data"] is not None and len(
                i["structured_data"]["json-ld"]) > 0]

        if bucket == "opengraph":
            subset = [i for i in result_list if "structured_data" in i.keys() and i["structured_data"] is not None and len(
                i["structured_data"]["opengraph"]) > 0]

        if bucket == "microformat":
            subset = [i for i in result_list if "structured_data" in i.keys() and i["structured_data"] is not None and len(
                i["structured_data"]["microformat"]) > 0]

        if bucket == "rdfa":
            subset = [i for i in result_list if "structured_data" in i.keys() and i["structured_data"] is not None and len(
                i["structured_data"]["rdfa"]) > 0]

        if bucket == "meta_content":
            subset = [i for i in result_list if "meta_content" in i.keys() and i["meta_content"] is not None]

        return subset
