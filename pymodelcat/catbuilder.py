import pandas as pd
from sciencebasepy import Weblinks
from sciencebasepy import SbSession
import requests
import json


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

        self.sb_wl = Weblinks()

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

    def get_models(self, model_catalog_id=None, fields='title,webLinks,contacts,tags'):
        if model_catalog_id is None:
            model_catalog_id = self.default_catalog_id

        models = list()

        items = self.sb.find_items({'parentId': model_catalog_id, 'fields': fields, 'max': 100})
        while items and 'items' in items:
            for item in items['items']:
                del item["link"]
                del item["relatedItems"]
                models.append(item)
            items = self.sb.next(items)

        return models

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

    def annotate_model_links(self, models=None, output_format="dataframe"):
        """Runs a list of models through a link annotation process

        :param models: List of ScienceBase Items describing models
        :param output_format: python list of dictionaries or dataframe (default)
        :param pickle_output: dump annotated items out to pickle file
        :return: Annotated model items in specified format
        """
        if models is None:
            models = self.get_models()

        annotated_items = list()

        for model in models:
            annotated_items.append(self.sb_wl.process_web_links(item=model))

        if output_format == "python":
            return annotated_items

        flattened_annotated_models = [self.flatten_json(i) for i in annotated_items]

        return pd.DataFrame(flattened_annotated_models)

    def flatten_json(self, y):
        """ From @amirziai https://github.com/amirziai/flatten

        :return: Flattened dictionary suitable for loading to dataframe
        """
        out = {}

        def flatten(x, name=''):
            if type(x) is dict:
                for a in x:
                    flatten(x[a], name + a + '_')
            elif type(x) is list:
                i = 0
                for a in x:
                    flatten(a, name + str(i) + '_')
                    i += 1
            else:
                out[name[:-1]] = x

        flatten(y)
        return out

    def link_miner(self, annotated_item, output_type="dataframe"):
        mined_data = list()

        for link in annotated_item["webLinks"]:
            try:
                record = dict(
                    model_id=annotated_item["id"],
                    model_sb_link=f'https://www.sciencebase.gov/catalog/item/{annotated_item["id"]}',
                    model_title=annotated_item["title"],
                    link_classification=link["title"],
                    link_url=link["uri"]
                )
                record["info_type"] = "title"
                record["info_source"] = "Title Meta Tag"
                record["info_content"] = link["annotation"]["meta_content"]["title"]
                mined_data.append(record)
            except:
                pass

            try:
                record = dict(
                    model_id=annotated_item["id"],
                    model_sb_link=f'https://www.sciencebase.gov/catalog/item/{annotated_item["id"]}',
                    model_title=annotated_item["title"],
                    link_classification=link["title"],
                    link_url=link["uri"]
                )
                record["info_type"] = "abstract"
                record["info_source"] = "Description Meta Tag"
                record["info_content"] = link["annotation"]["meta_content"]["description"]
                mined_data.append(record)
            except:
                pass

            try:
                record = dict(
                    model_id=annotated_item["id"],
                    model_sb_link=f'https://www.sciencebase.gov/catalog/item/{annotated_item["id"]}',
                    model_title=annotated_item["title"],
                    link_classification=link["title"],
                    link_url=link["uri"]
                )
                record["info_type"] = "abstract"
                record["info_source"] = "Abstract Meta Tag"
                record["info_content"] = link["annotation"]["meta_content"]["abstract"]
                mined_data.append(record)
            except:
                pass

            try:
                for prop in link["annotation"]["structured_data"]["microdata"][0]["properties"].keys():
                    record = dict(
                        model_id=annotated_item["id"],
                        model_sb_link=f'https://www.sciencebase.gov/catalog/item/{annotated_item["id"]}',
                        model_title=annotated_item["title"],
                        link_classification=link["title"],
                        link_url=link["uri"]
                    )
                    record["info_source"] = f"Microdata Property: {prop}"
                    record["info_type"] = prop
                    record["info_content"] = link["annotation"]["structured_data"]["microdata"][0]["properties"][prop]
                    mined_data.append(record)
            except:
                pass

            try:
                for prop, value in link["annotation"]["structured_data"]["opengraph"][0]["properties"]:
                    record = dict(
                        model_id=annotated_item["id"],
                        model_sb_link=f'https://www.sciencebase.gov/catalog/item/{annotated_item["id"]}',
                        model_title=annotated_item["title"],
                        link_classification=link["title"],
                        link_url=link["uri"]
                    )
                    record["info_source"] = f"Microformat Property: {prop}"
                    record["info_type"] = prop
                    record["info_content"] = value
                    mined_data.append(record)
            except:
                pass

            try:
                for prop, value in link["annotation"]["xml_meta_summary"].items():
                    record = dict(
                        model_id=annotated_item["id"],
                        model_sb_link=f'https://www.sciencebase.gov/catalog/item/{annotated_item["id"]}',
                        model_title=annotated_item["title"],
                        link_classification=link["title"],
                        link_url=link["uri"]
                    )
                    record["info_source"] = f"XML Metadata Summary: {prop}"
                    record["info_type"] = prop
                    record["info_content"] = value
                    mined_data.append(record)
            except:
                pass

        if output_type == "dataframe":
            return pd.DataFrame(mined_data)
        else:
            return mined_data

