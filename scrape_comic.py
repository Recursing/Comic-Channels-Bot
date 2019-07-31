from typing import Dict, Callable
import requests
import json
import re
from bs4 import BeautifulSoup


dispatcher: Dict[str, Callable] = {}


def scrape_for(domain):
    def wrapper(scrape_fun):
        dispatcher[domain] = scrape_fun
        return scrape_fun

    return wrapper


@scrape_for("www.instagram.com")
def scrape_instagram(url, soup):
    scripts = soup.find_all("script")
    script = [s for s in scripts if "window._sharedData" in s.text][0]
    m = json.loads(script.text.replace("window._sharedData = ", "")[:-1])
    user_data = m["entry_data"]["ProfilePage"][0]["graphql"]["user"]
    last_post = user_data["edge_owner_to_timeline_media"]["edges"][0]["node"]
    image_url = last_post["display_url"]
    description = last_post["edge_media_to_caption"]["edges"][0]["node"]["text"]
    return {"images": [image_url], "text": [url, description]}


@scrape_for("qwantz.com")
def scrape_qwantz(url, soup):
    comic = soup.find(class_="comic")
    a = soup.find(class_="topnav")
    mailto = str(list(a.children)[4]).split("?subject=")[-1].split(">contact<")[0]
    archive = re.search(
        '<!-- <span class="rss-title">(.*?)</span> -->', str(soup)
    ).group(1)
    if not comic["src"].startswith("http"):
        comic["src"] = "http://www.qwantz.com/" + comic["src"]
    return {
        "images": [comic["src"]],
        "text": [soup.title.string, comic["title"], mailto, archive],
    }


@scrape_for("smbc-comics.com")
def scrape_smbc(url, soup):
    comic = soup.find(id="cc-comic")
    votey = list(soup.find(id="aftercomic").children)[0]
    return {
        "images": [comic["src"], votey["src"]],
        "text": [soup.title.string, comic["title"]],
    }


@scrape_for("existentialcomics.com")
def scrape_existentialcomics(url, soup):
    comics = soup.findAll(class_="comicImg")
    alt_text = soup.find(class_="altText")
    if alt_text is not None:
        alt_text = alt_text.text.strip()
    else:
        alt_text = ""
    try:
        explanation = (
            soup.find(id="explainHidden").text.strip()
            or soup.find(id="explanation").text.strip()
        )
    except AttributeError:
        explanation = ""

    return {
        "images": [comic["src"].replace("//", "http://") for comic in comics],
        "text": [soup.title.string, alt_text, explanation],
    }


@scrape_for("phdcomics.com")
def scrape_phdcomics(url, soup):
    # new record for most horrible fix
    # soup = BeautifulSoup(str(soup).replace("REGULAR SCREEN--!>","-->"),"html.parser")
    # comic = soup.find(id="comic")
    # new new record for most horrible fix
    comic_src = soup("meta", property="og:image")[0].get("content")
    return {"images": [comic_src], "text": [soup.title.string.strip()]}


@scrape_for("www.giantitp.com")
def scrape_gianttip(url, soup):
    actual_url, title = next(
        (e["href"], e.text)
        for e in soup.findAll(class_="SideBar")
        if "comics/oots" in e["href"] and e["href"].endswith("html")
    )
    actual_html = requests.get("http://" + url + actual_url).text
    actual_soup = BeautifulSoup(actual_html, "html.parser")
    tds = actual_soup("td")
    images = [td("img") for td in tds]

    # TODO split very vertical comics
    image_urls = [
        "http://" + url + i[0]["src"]
        for i in images
        if len(i) == 1 and "/comics/images/" in i[0]["src"]
    ]
    return {"images": image_urls, "text": [title]}


@scrape_for("satwcomic.com")
def scrape_satw(url, soup):
    actual_url = soup(class_="btn-success")[0]["href"]
    actual_html = requests.get(actual_url).text
    actual_soup = BeautifulSoup(actual_html, "html.parser")
    comic = actual_soup("center")[2]("img")[0]["src"]
    description = actual_soup("span", attrs={"itemprop": "articleBody"})[0].text
    return {"images": [comic], "text": [actual_soup.title.string, description]}


@scrape_for("oglaf.com")
def scrape_oglaf(url, soup):
    comic = soup.find(id="strip")
    archive_html = requests.get("http://oglaf.com/archive/").text
    actual_url = BeautifulSoup(archive_html, "html.parser")("a")[0]["href"]
    ret = {
        "images": [
            oglaf_ll[sum(ord(e) for e in comic["src"]) % len(oglaf_ll)],
            comic["src"],
        ],
        "text": [soup.title.string, comic.get("alt", ""), comic.get("title", "")],
    }
    for i in range(2, 6):
        oc = requests.get(f"http://{url}{actual_url}{i}/").text
        oc_soup = BeautifulSoup(oc, "html.parser")
        o_comic = oc_soup.find(id="strip")
        if o_comic is None:
            break
        ret["images"].append(o_comic["src"])
        ret["text"].append(o_comic["alt"])
        ret["text"].append(o_comic["title"])
    return ret


@scrape_for("slatestarcodex.com")
def scrape_ssc(url, soup):
    last_post = soup("item")[0]
    url = last_post("guid")[0].text
    title = last_post("title")[0].text
    return {"images": [], "text": [title + "\n" + url]}


def get_content(url):
    headers = {"User-Agent": "Hi! Big fan <3"}
    html = requests.get("http://" + url, timeout=60, headers=headers).text
    soup = BeautifulSoup(html, "html.parser")
    return dispatcher[url.split('/')[0]](url, soup)


# See https://www.oglaf.com/ll.js
oglaf_ll = [
    "https://media.oglaf.com/loglines/storyteller.gif",
    "https://media.oglaf.com/loglines/sword-broken.gif",
    "https://media.oglaf.com/loglines/cloak-of-hiding.gif",
    "https://media.oglaf.com/loglines/love-is-a-dick.gif",
    "https://media.oglaf.com/loglines/plague-cancelled.gif",
    "https://media.oglaf.com/loglines/fairytale-ending.gif",
    "https://media.oglaf.com/loglines/one-sided-door.gif",
    "https://media.oglaf.com/loglines/datekeeper.gif",
    "https://media.oglaf.com/loglines/love-sport.gif",
    "https://media.oglaf.com/loglines/harold.gif",
    "https://media.oglaf.com/loglines/penis-infection_1.gif",
    "https://media.oglaf.com/loglines/life-magic.gif",
    "https://media.oglaf.com/loglines/chaos-army_1.gif",
    "https://media.oglaf.com/loglines/assassin-placebo_1.gif",
    "https://media.oglaf.com/loglines/animal-kisser_1.gif",
    "https://media.oglaf.com/loglines/vagina-polish.gif",
    "https://media.oglaf.com/loglines/penis-monster.gif",
    "https://media.oglaf.com/loglines/president-conan.gif",
    "https://media.oglaf.com/loglines/plotconvenience.gif",
    "https://media.oglaf.com/loglines/octothrone.gif",
    "https://media.oglaf.com/loglines/weteye.gif",
    "https://media.oglaf.com/loglines/STV.gif",
    "https://media.oglaf.com/loglines/plank.gif",
    "https://media.oglaf.com/loglines/skincare-corpses.gif",
    "https://media.oglaf.com/loglines/generous-selfish.gif",
    "https://media.oglaf.com/loglines/sausages.gif",
    "https://media.oglaf.com/loglines/wind-whisper.gif",
    "https://media.oglaf.com/loglines/wizard-caterer.gif",
    "https://media.oglaf.com/loglines/witness.gif",
    "https://media.oglaf.com/loglines/wedding-gift.gif",
    "https://media.oglaf.com/loglines/waxing.gif",
    "https://media.oglaf.com/loglines/true-love.gif",
    "https://media.oglaf.com/loglines/trap-palace.gif",
    "https://media.oglaf.com/loglines/time-travellers.gif",
    "https://media.oglaf.com/loglines/temporary-tatts.gif",
    "https://media.oglaf.com/loglines/tax-love.gif",
    "https://media.oglaf.com/loglines/stab-beast.gif",
    "https://media.oglaf.com/loglines/skeletons.gif",
    "https://media.oglaf.com/loglines/shower-sex.gif",
    "https://media.oglaf.com/loglines/sex-funeral.gif",
    "https://media.oglaf.com/loglines/sex-act.gif",
    "https://media.oglaf.com/loglines/self-sacrifice.gif",
    "https://media.oglaf.com/loglines/secret-palace.gif",
    "https://media.oglaf.com/loglines/sceptic-ghost.gif",
    "https://media.oglaf.com/loglines/reflection.gif",
    "https://media.oglaf.com/loglines/real.gif",
    "https://media.oglaf.com/loglines/pygmalion.gif",
    "https://media.oglaf.com/loglines/pulling-knobs.gif",
    "https://media.oglaf.com/loglines/problems.gif",
    "https://media.oglaf.com/loglines/pity-sex.gif",
    "https://media.oglaf.com/loglines/pick-truth.gif",
    "https://media.oglaf.com/loglines/parody-animals.gif",
    "https://media.oglaf.com/loglines/parents.gif",
    "https://media.oglaf.com/loglines/oral-doubt.gif",
    "https://media.oglaf.com/loglines/nostalgia-man.gif",
    "https://media.oglaf.com/loglines/never-stopped-loving.gif",
    "https://media.oglaf.com/loglines/neer.gif",
    "https://media.oglaf.com/loglines/necromancer.gif",
    "https://media.oglaf.com/loglines/monster-eggs.gif",
    "https://media.oglaf.com/loglines/medical.gif",
    "https://media.oglaf.com/loglines/matador.gif",
    "https://media.oglaf.com/loglines/looting.gif",
    "https://media.oglaf.com/loglines/logistically.gif",
    "https://media.oglaf.com/loglines/legally-mum.gif",
    "https://media.oglaf.com/loglines/lava.gif",
    "https://media.oglaf.com/loglines/job-interviews.gif",
    "https://media.oglaf.com/loglines/innuendo-tonight.gif",
    "https://media.oglaf.com/loglines/infographic_7.gif",
    "https://media.oglaf.com/loglines/hygiene.gif",
    "https://media.oglaf.com/loglines/glitter-mines.gif",
    "https://media.oglaf.com/loglines/giantess-fetish.gif",
    "https://media.oglaf.com/loglines/get-lost.gif",
    "https://media.oglaf.com/loglines/garage-sale.gif",
    "https://media.oglaf.com/loglines/fucktoplasm.gif",
    "https://media.oglaf.com/loglines/fuck-dude.gif",
    "https://media.oglaf.com/loglines/flight-mode.gif",
    "https://media.oglaf.com/loglines/fire-expert.gif",
    "https://media.oglaf.com/loglines/finest-free-ass.gif",
    "https://media.oglaf.com/loglines/figure-skating.gif",
    "https://media.oglaf.com/loglines/ferryman_1.gif",
    "https://media.oglaf.com/loglines/expect-disappointment.gif",
    "https://media.oglaf.com/loglines/evil-bath.gif",
    "https://media.oglaf.com/loglines/envy.gif",
    "https://media.oglaf.com/loglines/elevator_1.gif",
    "https://media.oglaf.com/loglines/dreams_1.gif",
    "https://media.oglaf.com/loglines/death-pencils.gif",
    "https://media.oglaf.com/loglines/crowdsource.gif",
    "https://media.oglaf.com/loglines/colic.gif",
    "https://media.oglaf.com/loglines/cloudy.gif",
    "https://media.oglaf.com/loglines/burglaries.gif",
    "https://media.oglaf.com/loglines/broccoli.gif",
    "https://media.oglaf.com/loglines/blame.gif",
    "https://media.oglaf.com/loglines/best-lover.gif",
    "https://media.oglaf.com/loglines/be-an-asshole_1.gif",
    "https://media.oglaf.com/loglines/attractive_1.gif",
    "https://media.oglaf.com/loglines/articlefucker.gif",
    "https://media.oglaf.com/loglines/arc-stupid.gif",
    "https://media.oglaf.com/loglines/ambulance.gif",
    "https://media.oglaf.com/loglines/all-our-fault.gif",
    "https://media.oglaf.com/loglines/abbatoir.gif",
]
