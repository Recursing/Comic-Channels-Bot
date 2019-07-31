import traceback
import urllib.request
import logging
import json

# import telegram
import dataset

from scrape_comic import get_content


# API_KEY =
# bot = telegram.Bot(API_KEY)


class DummyBot:
    def sendMessage(self, *args, **kwargs):
        print(f"Called sendMessage with {args} {kwargs}")

    def sendPhoto(self, *args, **kwargs):
        print(f"Called sendPhoto with {args} {kwargs}")


bot = DummyBot()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

URLS = {
    "smbc-comics.com": -1001083921558,
    "qwantz.com": -1001091660369,
    "existentialcomics.com": -1001078756889,
    "phdcomics.com": -1001086129161,
    "www.giantitp.com": -1001089642885,
    "satwcomic.com": -1001061049786,
    "oglaf.com": -1001055865432,
    "www.instagram.com/ColazioneArcobaleno/": -1001213449695,
    "slatestarcodex.com/feed": -1001261320698,
    "www.instagram.com/nathanwpylestrangeplanet": -1001262434036,
}


db = dataset.connect("sqlite:///comicdb.db")
table = db["comics"]


def is_already_sent(content):
    return bool(
        table.find_one(
            comic=url,
            text=json.dumps(content["text"]),
            images=json.dumps([image_id(i) for i in content["images"]]),
        )
    )


def last_sent(url):
    comics_sent = list(table.find(comic=url))
    row = comics_sent[-1] if comics_sent else {"text": "[]", "images": "[]"}
    return {"text": json.loads(row["text"]), "images": json.loads(row["images"])}


def image_id(image_url):
    return image_url.split("/")[-1].split("?")[0]


def get_changes(new_content, old_content):
    # TODO image and text similarity and differences
    return {
        "text": [t for t in new_content["text"] if t not in old_content["text"]],
        "images": [
            i for i in new_content["images"] if image_id(i) not in old_content["images"]
        ],
    }


def send_url_updates(url):
    content = get_content(url)
    logging.info("Scraped {}, title: {}".format(url, content["text"][0]))
    if is_already_sent(content):
        return
    logging.info("new comic! {}".format(content))
    old_content = last_sent(url)
    updates = get_changes(content, old_content)
    if not any(updates.values()):
        return

    # Send comic title
    if content["text"][0] == updates["text"][0]:
        title_message = "[{}](http://{})".format(updates["text"][0], url)
        bot.sendMessage(
            chat_id=channel,
            text=title_message,
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )
        updates["text"].pop(0)

    for image in updates["images"]:
        image = urllib.request.quote(image, safe="/:=?")
        assert image.startswith("http")
        urllib.request.urlretrieve(image, "tmp_image.png")
        bot.sendPhoto(chat_id=channel, photo=open("tmp_image.png", "rb"))

    for text in updates["text"]:
        for i in range(0, len(text), 4000):
            bot.sendMessage(chat_id=channel, text=text[i : i + 4000])

    table.insert(
        {
            "comic": url,
            "text": json.dumps(content["text"]),
            "images": json.dumps([image_id(i) for i in content["images"]]),
        }
    )


if __name__ == "__main__":
    for url, channel in URLS.items():
        try:
            send_url_updates(url)
        except Exception as e:
            logging.error("Exception... {} {}".format(url, e))
            print("=======\n".join(traceback.format_tb(e.__traceback__)))
            bot.sendMessage(
                80906134,
                "Exception {} {}".format(
                    url, "=======\n".join(traceback.format_tb(e.__traceback__))
                ),
            )
            continue
