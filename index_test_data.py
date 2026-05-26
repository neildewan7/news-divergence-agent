import os
from dotenv import load_dotenv
from elasticsearch import Elasticsearch, helpers

load_dotenv()

es_client = Elasticsearch(
    os.getenv("ELASTICSEARCH_ENDPOINT"),
    api_key=os.getenv("ELASTICSEARCH_API_KEY"),
)

INDEX_NAME = "noto-earthquake-articles"

index_mapping = {
    "mappings": {
        "properties": {
            "title": {"type": "text", "copy_to": "semantic_field"},
            "body": {"type": "text", "copy_to": "semantic_field"},
            "source": {"type": "keyword"},
            "language": {"type": "keyword"},
            "publish_date": {"type": "date"},
            "event_id": {"type": "keyword"},
            "semantic_field": {"type": "semantic_text"},
        }
    }
}

if not es_client.indices.exists(index=INDEX_NAME):
    es_client.indices.create(index=INDEX_NAME, body=index_mapping)
    print(f"Created index: {INDEX_NAME}")
else:
    print(f"Index already exists: {INDEX_NAME}")

# 5 fake articles, same event, divergent details — this is your tiny demo case
test_articles = [
    # --- ENGLISH SOURCES ---
    {
        "title": "Japan earthquake kills at least 48, thousands evacuated",
        "body": """
            Japan reports dozens of fatalities after series of strong earthquakes

            Thousands evacuated from Noto Peninsula and Prime Minister Fumio Kishida says he will personally lead national response to disaster.

            Videos show moments earthquakes struck Japan on New Year's Day

            01:43
            Get more news
            on

            Share
            Add NBC News to Google

            Jan. 1, 2024, 5:38 PM GMT+9 / Updated Jan. 2, 2024, 5:40 PM GMT+9

            By Arata Yamamoto, Larissa Gao and Corky Siemaszko

            TOKYO — Japan was struck by a series of powerful earthquakes on New Year's Day that killed at least 48 people, reduced hundreds of buildings to rubble, and forced tens of thousands to flee to higher ground.

            NBC News Icon
            Subscribe to read this story ad-free

            Get unlimited access to ad-free articles and exclusive content.

            arrow

            Dozens of survivors were being treated at hospitals across the Ishikawa prefecture and the emergency rooms were expected to become even more crowded as rescue crews free people believed to be still trapped in the ruins of homes and buildings.

            The Japanese public broadcaster NHK TV summed-up the situation with a grim headline: "Homes have collapsed, there are people unconscious."

            Potentially complicating the rescue efforts was a forecast that could include snow Tuesday in this region some 325 miles west of Tokyo, and the fact that so many roads have been damaged that manpower and supplies may have to be delivered by boat.

            Meanwhile, firefighters were battling blazes that devoured some 50 buildings in a market area within the city of Wajima, NHK reported, citing Ishikawa officials.

            Those buildings were believed to be largely unoccupied when, according to the Japan Meteorological Agency, the quakes hit off the Ishikawa coast a little after 4 p.m. local time (2 a.m. ET), with one reaching a magnitude of 7.6.

            Japanese Prime Minister Fumio Kishida told reporters he would personally lead the nation's disaster response and has already been in touch with the mayors of Wajima and Suzu, which is another city on the Noto Peninsula hit hard by the quakes.

            Not long after, the White House issued a statement pledging to help Japan if needed.

            "My administration is in touch with Japanese officials, and the United States stands ready to provide any necessary assistance for the Japanese people," President Joe Biden said.

            So far, three of the reported deaths — two in Nanao City and one in Shika Town — were due to building collapses, Japanese broadcaster NTV reported, citing information from local police. Eight people were confirmed dead and seven people were seriously injured in Wajima city, according to NHK. The two other deaths were reported in unspecified locations.

            Cracks are seen on the ground in Wajima in Japan's Ishikawa prefecture on Jan. 1, 2024, following an earthquake.

            Cracks on the ground Monday in Wajima in Japan's Ishikawa prefecture. Kyodo News via AP

            Kishida said search-and-rescue teams have been dispatched to the stricken cities, but manpower and supplies might have to be brought in by boat because many roads in the area are damaged.

            Also, large swaths of the area were without power, water or cellphone service as a result of the quakes, Kishida said.

            "As the casualties are starting to become apparent, it is now a race against time," Kishida said at a news conference. "We must work on rescuing everyone, especially those buried under collapsed buildings. I call on all to utilize all available methods, including deploying the Self-Defense Force, and to do everything possible to expedite the recovery and repair of damaged infrastructure as soon as possible."

            Tsunami warnings had been issued in the wake of the quakes in Ishikawa as well as the coastal prefectures of Niigata and Toyama, where 33,000 buildings had lost power as of 6 p.m. (4 a.m. ET), according to the Hokuriku Electric Power company.

            The Japanese public broadcaster NHK TV warned the quakes could churn-up 17-foot tall waves and urged people on the entire west coast to evacuate.

            Those tsunami warnings were lifted later Monday and, thus far, the tallest wave reported was around 4 feet tall and detected at the port in the city of Wajima, the broadcaster reported.

            An aerial photo shows a fire due to a massive earthquake in Wajima City, Ishikawa Prefecture on Jan. 1, 2024.

            An aerial photo shows a fire due to a massive earthquake in Wajima City in Japan's Ishikawa Prefecture on Monday. Takehito Kobayashi / The Yomiuri Shimbun via AP

            The quakes were so powerful they were felt on the other side of the country in Tokyo, according to the broadcaster.

            A video posted to X showed a train station in Kanazawa, the capital of Ishikawa Prefecture, shaking and losing power during an earthquake. Another showed a family clinging on to whatever they could as their apartment in Kanazawa rocked wildly.

            Other videos posted to social media showed houses in some areas with roofs caved in and door frames falling off while surrounding trees fall to the ground. In some supermarkets, goods were scattered as the ground shook.

            In Wajima, the quake flattened a lacquerware company and at least 30 homes in the city, trapping dozens of people under the rubble, NHK reported, citing the local fire department and a statement from the local government.

            Several people with minor head or other injuries from falling objects were treated at Wajima Municipal Hospital, officials there said.

            In Nanao City, which is located on the same peninsula, landslides, cracked roads, and collapsed homes were also reported, local police said.

            Collapsed houses after an earthquake in Anamizu Town in Japan's Ishikawa Prefecture on Jan. 1, 2024.

            Collapsed houses after an earthquake in Anamizu Town in Japan's Ishikawa Prefecture on Monday. Noboru Hosono / The Yomiuri Shimbun via AP

            In Suzu, the collapse of a two-story house was caught on camera by an NHK crew. Other footage showed one large isolated wave crashing off the coast of the city.

            Earlier, Japanese officials announced it was sending military assistance to the hardest-hit areas but none of the nuclear reactors operating in the region had been damaged.

            Train service in and out of the area was suspended and the airport that serves the cities on the Noto Peninsula was shut down.

            Arata Yamamoto reported from Tokyo, Larissa Gao reported from Hong Kong, and Corky Siemaszko from New York City.
        """,  # paste NBC News Jan 2 article here
        "source": "NBC News",
        "language": "en",
        "publish_date": "2024-01-02",
        "event_id": "noto-earthquake-2024-01",
    },
    {
        "title": "Dozens killed in Japan earthquakes as temblors continue rocking country's west",
        "body": """
            Dozens killed in Japan earthquakes as temblors continue rocking country's west

            Updated on: January 2, 2024 / 10:59 AM EST / CBS/AP

            Add CBS News on Google

            Wajima, Japan — A series of powerful earthquakes hit western Japan, leaving at least 55 people dead, according to Japan's state broadcaster NHK, and damaging thousands of buildings, vehicles and boats. Officials warned people in some areas on Tuesday to stay away from their homes because of the risk of more strong quakes, as aftershocks continued to shake Ishikawa prefecture and nearby areas a day after a magnitude 7.6 temblor slammed the area on Monday afternoon.

            55 people were confirmed dead in Ishikawa, with the casualties concentrated in the cities of Wajima and Suzu, according to NHK and other media outlets. At least fourteen others were said by officials to have been seriously injured, while damage to homes was so great that it could not immediately be assessed.

            Japanese media reports said tens of thousands of homes were destroyed. Government spokesperson Yoshimasa Hayashi said 17 people were seriously injured and gave a slightly lower death tally, while saying he was aware of the prefecture's tally.

            TOPSHOT-JAPAN-QUAKE

            Firefighters inspect collapsed wooden houses in Wajima, Ishikawa prefecture, Japan, Jan. 2, 2024, a day after a major earthquake struck the Noto region.

            KAZUHIRO NOGI/AFP/Getty

            Water, power and cellphone service were still down in some areas, and residents expressed sorrow about their destroyed homes and uncertain futures.

            "It's not just that it's a mess. The wall has collapsed, and you can see through to the next room. I don't think we can live here anymore," Miki Kobayashi, an Ishikawa resident, said as she swept around her house, which she said was also damaged in a 2007 earthquake.

            Japan's military dispatched 1,000 soldiers to the disaster zones to join rescue efforts, Prime Minister Fumio Kishida said Tuesday.

            "Saving lives is our priority and we are fighting a battle against time," he said. "It is critical that people trapped in homes get rescued immediately."

            A quake with a preliminary magnitude of 5.6 shook the Ishikawa area as he was speaking.

            Firefighters managed to bring a fire under control in Wajima city which had reddened the sky with embers and smoke. Japan's Kyodo news agency, citing Ishikawa prefectural officials, said several fires in Wajima had engulfed more than 200 structures and there were more than a dozen reports of people being trapped under rubble in the city.

            The quake has also caused injuries and structural damage in Niigata, Toyama, Fukui and Gifu prefectures.

            "It is extremely difficult for vehicles to enter northern areas of the Noto Peninsula," Prime Minister Fumio Kishida said at a press conference, adding the central government has been coordinating shipment of relief supplies using ships.

            JAPAN-QUAKE

            This aerial photo provided by Jiji Press shows smoke rising from an area following a large fire in Wajima, in Japan's western Ishikawa prefecture, Jan. 2, 2024, a day after a major earthquake struck the Noto region.

            STR/JIJI PRESS/AFP/Getty

            Nuclear regulators said several nuclear plants in the region were operating normally. A major quake and tsunami in March 2011 caused three reactors to melt and release large amounts of radiation at a nuclear plant in northeastern Japan.

            News videos showed rows of collapsed houses. Some wooden structures were flattened and cars were overturned. Half-sunken ships floated in bays where tsunami waves had rolled in, leaving a muddied coastline.

            Japanese media, quoting the Ministry of Transport, said 500 people were trapped at Noto Airport in Wajima, including airport staff, passengers and local residents. Because the airport's windows were shattered and glass and debris scattered around the terminal, all were sheltering in the parking lot, inside rental cars and tour buses, the reports said, with the airport not scheduled to reopen until Jan. 4.

            On Monday, the Japan Meteorological Agency issued a major tsunami warning for Ishikawa and lower-level tsunami warnings or advisories for the rest of the western coast of Japan's main island of Honshu, as well as for the northern island of Hokkaido.

            The warning was downgraded several hours later, and all tsunami warnings were lifted as of early Tuesday. Waves measuring more than 3 feet hit some places.

            The agency warned that more major quakes could hit the area over the next few days.

            Damages After Strong Earthquake Hits Northwestern Japan

            A damaged vehicle is pinned under a collapsed house following an earthquake in Nanao, Ishikawa Prefecture, Japan, Jan. 2, 2024.

            Soichiro Koriyama/Bloomberg/Getty

            People who were evacuated from their houses huddled in auditoriums, schools and community centers. Bullet trains in the region were halted, but service was mostly restored by Tuesday afternoon. Sections of highways were closed.

            Weather forecasters predicted rain, setting off worries about already crumbling buildings and infrastructure.

            The region includes tourist spots famous for lacquerware and other traditional crafts, along with designated cultural heritage sites.

            U.S. President Joe Biden said in a statement that his administration was "ready to provide any necessary assistance for the Japanese people."

            Japan is frequently hit by earthquakes because of its location along the "Ring of Fire," an arc of volcanoes and fault lines in the Pacific Basin.

            Over the last day, the nation has experienced about a hundred aftershocks.
            """,  # paste Reuters Jan 3-4 article here
        "source": "CBS News",
        "language": "en",
        "publish_date": "2024-01-02",
        "event_id": "noto-earthquake-2024-01",
    },
    {
        "title": "Noto Peninsula earthquake: Red Cross reports 241 confirmed deaths",
        "body": """
            Operation Update No.30 : 2024 Noto Peninsula Earthquake: The Japanese Red Cross Society's Response

            2024.02.20

            The Japanese Red Cross Society would like to express our sincere condolences and sympathy toward the people affected by the massive earthquake which hit Japan on 1 January 2024. Our relief teams have been working around the clock to save lives, protect health and dignity of the affected people in Noto Peninsula.

            1. Situation

            - On 1 January 2024 at 16:10 (Japan Standard Time), a magnitude 7.6 earthquake struck the Noto Peninsula in Ishikawa Prefecture, Japan. As the epicenter was very shallow, large tremors were observed in many places and a tsunami warning was issued. Since then, more than 1,500 aftershocks have followed the main shock.

            - The tsunami damaged at approximately 160 hectares in Suzu City and Noto City. Power and water supplies were still cut, communications were disrupted.

            - Some districts are isolated with roads cut off and food, water, blanket and fuel, basic needs are still in short supply.

            - The quake caused fires in some cities and it is estimated that hundreds of houses were burnt down.

            - According to the Japan Nuclear Regulation Authority, no issues have been found with reactors at nuclear power plants in the affected area, including the Shika nuclear power plant in Ishikawa Prefecture.

            画像

            Noto Peninsula earthquake in 2024 - epicenter and severely affected areas -

            2. Impacts

            - The Japanese Government applied the Disaster Relief Act towards 35 cities, 11 towns and 1 village in 4 prefectures including Niigata, Toyama, Ishikawa and Fukui in order to lead the national-level relief operations.

            - As of 14:00 on 16 February, the local government confirmed 241 deaths in Ishikawa prefecture. On top of this, 9 people in Ishikawa prefecture remain unaccounted for.

            - At least 1,296 people were injured.

            - More than 60,614 houses are reported to be collapsed/damaged, which brought about 12,929 people remained in 521 evacuation centers.

            3. Japanese Red Cross Society's Response

            - The Japanese Red Cross Society (JRCS) began its response immediately after the disaster, and its chapters in the affected areas are working with Red Cross hospitals and Red Cross Blood Centers to assess the extent of the damage.

            画像

            - As of 10:00 on 19 February;

            (1) 74 staff members have been dispatched to the Prefectural Disaster Prevention Headquarters to obtain the latest information and to organize emergency relief.

            (2) 297 Emergency Medical Relief Teams have been dispatched to the hospitals, social welfare facilities, evacuation centers, etc. in Ishikawa prefecture. The team consists of a doctor, nurses and administrators from Red Cross hospitals all over Japan. At the moment, 16 out of 297 teams are assessing the situation, delivering patients to the hospitals, transporting medicines and providing mobile clinic services.

            (3) 93 Disaster Medical Coordination teams have been dispatched to Ishikawa Prefecture in order to arrange and coordinate the emergency medical operation with other stakeholders.

            (4) 84 Nurses from Red Cross hospitals have been deployed to Anamizu General Hospital, Wajima Municipal Hospital, and Ushitsu General Hospital to back up its capacity of providing medical care toward the affected people.

            (5) 71 staff members from JRCS headquarters and hospitals were deployed to its Ishikawa chapter to set up and coordinate psychosocial support (PSS) programme. The JRCS Emergency Medical Teams provide PSS to the affected people.

            (6) 11 staff members from JRCS headquarters and 3 Red Cross Hospitals are setting up a temporary water distribution system at evacuation centers located in 2 elementary schools in Nanao city. The water supply service began on 22 January by pumping up water from the swimming pool, purifying it with the purification method, and distributing it through temporary water pipe. The temporary shower rooms and laundry machines are also set up by the JRCS to improve the personal and public hygiene of the evacuees. This system is a part of JRCS’s ERU WATASAN and Laundry modules, which have originally been prepared for the JRCS’s international relief operation at emergency.

            VOICE:

            - "It is amazing that not only cold but also hot water is now supplied. I feel as if everything were miracle even though it was quite usual in my daily life before the earthquake came. I really appreciate for the assistance from the JRCS."

            - "Using the newly installed water tap, we will be able to flush the toilet."

            - "I had to stand in a long line from 6:00am to wash my cloths at the coin laundry shop, but thank to the JRCS, it has become easy with these laundry machines in the evacuation center."

            (7) 11 staff members (7 doctors and 4 coordinators) joined the assessment team of the National Cabinet Office.

            (8) 28 Logistics support members have been working in Suzu-city in Ishikawa prefecture.

            (9) 16,005 blankets, 5,230 sleep comfort kits, 3,400 portable toilets, 2,224 family emergency sets, 500 towels, 1900 stockings, 50 cassette stoves, and other relief items were distributed to the affected people. 43 partitions were also delivered to keep privacy in the evacuation centers.

            (10) 1,368 Red Cross Volunteers have been leading a needs assessment, transporting and delivering relief items, and serving at a soup kitchen in the affected area. They also manage the Red Cross Volunteer Coordination Center.

            (11) 2 Caregivers from ReCross Hiroo have been deployed to the Ishikawa Sports Center to provide disaster welfare support at the request of the Ministry of Health, Labour and Welfare.

            20240104-6bf7d69026661d65ef9ef804582b29f423a0e113.jpg Blanket ©Japanese Red Cross Society

            20240104-e4c438617c49837d14de402a6ca6dcbbcbbfe830.JPG Sleeping comfort kits ©Japanese Red Cross Society

            20240104-714d0d71301aaca53a688dad2bce4cfd2ebefa2e.jpg Family emergency set ©Japanese Red Cross Society

            20240111-216c4821e8c21f9dc089742372d1829f843aeb58.jpg

            Transportation of emergency relief items ©Japanese Red Cross Society

            Red Cross Volunteers distributing relief items (Wajima, Ishikawa) @Japanese Red Cross Society.jpg

            Red Cross Volunteers distributing relief items (Wajima, Ishikawa) ©Japanese Red Cross Society

            20240111-a10ee25e15413cd386cf2a0fd5d369c88ce31a8e.jpg

            Logistics support team setting up a tent ©Japanese Red Cross Society

            A JRCS Relief Team providing psychosocial support (Anamizu town, Ishikawa prefecture).png

            JRCS Relief Team providing psychosocial support (Anamizu, Ishikawa)

            JP20240106_1682_atsushishibuya.png

            Treatment of an injured victim (Suzu, Ishikawa)

            Rescue team making rounds at an isolated facility_Suzu City_Ishikawa Prefecture.jpg

            Mobile clinic at a social welfare facility isolated by the earthquake (Suzu, Ishikawa)

            ©Japanese Red Cross Society

            20240111-2071c68df173c3f1da43b215041b76848662f475.jpg

            Mobile clinic at an evacuation center (Nanao, Ishikawa) ©Japanese Red Cross Society

            20240111-253bd5346ada438a0b7b0dff39ea756a6408f2e0.jpg Mother and child health assistance (Wajima, Ishikawa) ©Japanese Red Cross Society

            20240122-840bfd109139bc9f2da4ce908e5deccd42d39efb.jpg

            Installation of water supply system at an evacuation center (Nanao, Ishikawa) ©Japanese Red Cross Society

            20240122-2be622c71eae890e04fea750926c70adcd3130a8.png

            Installation of water supply system at an evacuation center (Nanao, Ishikawa) ©Japanese Red Cross Society

            20240123-21b5de07905a15e2cbc31bff6074c3e39931f45b.jpg Temporary water tap at the evacuation center (Nanao, Ishikawa) ©Japanese Red Cross Society

            20240123-5ecb44ba1b96b326750664a68a3afdbf8efe4a71.jpg Laundry machine (front) and shower booth (back) installed by the JRCS (Nanao, Ishikawa) ©Japanese Red Cross Society

            shower.png

            "I am feeling good after taking a shower!" © Japanese Red Cross Society

            4. Useful Information (for those who lost contact with their family members)

            Restoring Family Links (RFL)

            With its high standard of the Personal Data Protection in Japan, the Japanese Red Cross Society (although we can provide tracing services only for those who lost contact with their family members as a result of conflict, disaster or other humanitarian emergencies through the Red Cross channel) recommends you to reach out the respective affected prefecture of Ishikawa directly that has been in close touch with each municipality and compiling then even publishing the list of people whose safety is unknown.

            Information on the 2024 Noto Peninsula Earthquake (Task Force Headquarters/Damage Situation) | Ishikawa Prefecture (www-pref-ishikawa-lg-jp.translate.goog)

            Although the service is only available in Japanese, you also can use Disaster Emergency Message Dial (177).

            A free Wi-Fi service "00000JAPAN" is also available at this moment in the affected area.

            *Please note that it is not a secured Wi-Fi.

            Given the hardship in restoring the telecommunication infrastructure across the Peninsula, Japanese major telecommunication carriers are now providing the Starlink service free of charge to the evacuation center.
            """,  # paste Red Cross Feb 16 update here
        "source": "Japanese Red Cross",
        "language": "en",
        "publish_date": "2024-02-16",
        "event_id": "noto-earthquake-2024-01",
    },
    # --- JAPANESE SOURCES ---
    {
        "title": "能登半島地震の災害関連死、直接死の2倍に",
                "body": """
        能登半島地震（のとはんとうじしん）は、2024年（令和6年）1月1日16時10分 (JST) に、石川県の能登半島地下16 km[20]、鳳珠郡穴水町の北東42 km[4]、輪島市からは東北東に約30 km[21]の珠洲市内で発生した内陸地殻内地震[22]。地震の規模はМ7.6[23][24][25]（気象庁）で、輪島市と羽咋郡志賀町で最大震度7を観測した[6]。震度7が記録されたのは、2018年の北海道胆振東部地震以来、観測史上7回目となる。

        能登半島西方沖から佐渡島西方沖にかけて伸びる活断層を震源とする[9]。能登地方では2018年ごろから群発地震が発生しており[26]、特に2020年12月ごろから本震までの地震回数はそれまでの約400倍に増加していた[27][28]（前震と余震の詳細は能登群発地震を参照）[6][14]。

        この地震により日本海沿岸の広範囲に津波が襲来した[5]ほか、奥能登地域を中心に土砂災害、火災、液状化現象、家屋の倒壊、交通網の寸断が発生し、甚大な被害をもたらした[29]。元日に発生したこともあり、帰省者の増加による人的被害の拡大や[30]、新年行事の自粛[31]など社会的にも大きな影響があり、本地震の翌日には被災地の救援のため派遣された航空機による航空事故（羽田空港地上衝突事故）も発生した[32]。建物の耐震強度を地域により割り引く「地震地域係数」があるが、輪島市などが0.9でコンクリート建築物も被害が発生したことから、国土交通省では基準を全国一律に見直す検討が始まった[33]。

        名称

        この地震の本震は、気象庁が2018年に定めた陸域で発生した地震の命名の要件[34]のうち「Ｍj7.0以上（深さ100 km以浅）かつ最大震度5強以上」という要件を満たしていた。また、この要件においては定めた名称が一連の地震活動全体を指すことも定められていた[34]。そのため、気象庁は発生当日の18時過ぎから開いた記者会見において、最大震度7の本震を含む2020年12月以降の一連の地震活動（能登群発地震）を「令和6年能登半島地震」（英：The 2024 Noto Peninsula Earthquake）と命名した[1][35][36]。この名称の中には石川県が「令和5年奥能登地震」と命名した2023年5月5日の地震も含まれている[37]。地震活動に対して気象庁が命名を行うのは、2018年（平成30年）9月の北海道胆振東部地震以来約5年4か月ぶりで[1]、気象庁が初めて地震活動に対する命名を行った1960年のチリ地震津波以降33回目であった[37][38]。

        被災地の石川県を拠点とする地方紙である『北國新聞』や同新聞の傘下で富山県を拠点とする『富山新聞』などの一部マスメディア、石川県津幡町など被災地の一部の広報紙などにおいては主に見出しにおいて1.1大震災[21][39][40]という呼称を用いている。地震が発生して間もない時期には能登大地震[41]、石川大震災[42]という名称も用いられていた。日本共産党の機関紙『しんぶん赤旗』では主に見出しにおいて能登半島1.1地震という呼称を用いている[43]。その他、見出しで単に能登地震と表現される場合もある。

        地震のメカニズム

        断層運動と震源周辺の活断層

        16時6分に発生した地震の震源球

        日本海東縁変動帯の地図

        この地震は日本海東縁変動帯の西端で発生しており[44]、発震機構は、北西 - 南東方向に圧力軸を持つ逆断層型であった。また発震機構と地震活動の分布および衛星測位システム (GNSS) 観測の解析から、震源断層は北東 - 南西に延びる150 km程度の、主として南東傾斜の逆断層であると考えられている[9]。防災科学技術研究所の推計では、震源断層の走向が213度・47度、傾斜が41度・50度、すべり角が79度・99度などとなっている[3]。また、気象庁は29か所の観測点のデータから、この地震のセントロイド（断層の全ての動きを1つの空間的・時間的な点に代表させた場合の座標並びに時刻）時刻を16時10分42.3秒、セントロイド位置を北緯37度29.2分 東経137度15.6分[注釈 4]の深さ15 kmの位置（理論的に計算された波形と実際に観測された波形の一致度を表すバリアンスリダクションが81 %）、地震モーメント (Mo)と6方向のモーメントテンソル解を1020 N・mの単位でMoが2.14、Mrrが1.89、Mttが-0.83、Mffが1.15、Mrtが-0.23、Mrfが-0.6、Mtfが-1.1（断層の押し引きの境界と断層面のずれを表す非ダブルカップル (D.C.) 成分比は-0.04）と計算している[45]。地震調査委員会委員長で東京大学名誉教授の平田直は地震翌日の会見で、この断層は既知のものではないと説明していた[46]。この地震以降、新潟県佐渡島の西方から能登半島西方にかけての約150 kmの範囲にわたって、地震活動域が広がっており[9]、余震が断続的に続いている[47]。震源域の東端は富山トラフの西端付近にある。震源域の西端は2007年の能登半島地震の震源域にかかり海士岬付近まで広がっているが、1993年の能登半島沖地震の震源域にはかかっていない[48]。地震学者の遠田晋次は、日本列島の大きさを考慮すれば日本国内で100 km以上の長さの活断層が動く内陸性地震が発生することは稀であると述べている[49]。この地震によって破壊された全ての活断層が破壊されるまでには約40秒の時間がかかっている[50]。P波はヨーロッパ、北アメリカ、オセアニアなど世界各地で観測され、ウクライナのキーウ（キエフ）で338.3 μm、カザフスタンのマカンチで301.2 μm、フィリピンのダバオで202.1 μm、西オーストラリア州ナロジンで197.5 μm、ミッドウェー島で90.2 μm、アメリカ合衆国マサチューセッツ州ハーバードで20.9 μm、ロシアのビリビノで18.7 μm、グリーンランドのカンゲルルススアークで3.2 μmなどの振幅が計測されている[5]。

        宍倉正展らの研究によれば、能登半島には新生代第四紀更新世チバニアン期（中期更新世、約78万年前から約13万年前）以降の海成段丘が発達しており、完新世に形成された3段の低位段丘面も認められていた[51]。これは、数十万年以上前からごく最近まで地盤の隆起が発生していたことを示しており、この隆起は主に地震時の断層運動によって生じた[52]。本地震では能登半島北部で最大約4 mの隆起が生じており（後述）、鹿磯漁港の北では約3.6 mの隆起により波食棚が干上がった様子が確認された。宍倉らはこれらを4段目の完新世低位段丘面が新たに生じたことを意味していると解釈している[53]。

        東京大学地震研究所の石山ら[54]や産総研の宍倉[51]によると、2024年の地震で大きな隆起が観測された地域では、宍倉らの研究で報告された完新世低位段丘面も周囲と比べて標高が高く、本地震による隆起量と低位段丘面の旧汀線高度（波打ち際の高さ）が近似している。この事実は、この地域において本地震のようなマグニチュード7級の地震が繰り返し発生しており、それに伴って低位段丘面が形成されていった可能性があることを示していると考えられている。また、宍倉は地震直前の段階で、奥能登地震（2023年5月5日、Mj6.5）と同程度の規模の地震では説明できない隆起が過去に能登半島で発生した痕跡があり、今後奥能登地震より更に大きな地震が発生する可能性があることを論文で述べようとしていた矢先にその可能性が現実となったこと、現に本地震ほどの大地震が発生したために1 m未満の隆起が少しずつ堆積したという仮説を検討する必要がなくなったと述べている[55]。ただし、西村卓也はMj7クラスの地震が起きるとしてもそれはMj7台の前半であると考えており、この地震の本震で発生したMj7.6は「ワーストケースをさらに上回る」ものであったと述べている。一方で、地震が起きない可能性より起きる可能性の方が高いと言える状況ではなかったことから、住宅の耐震化を進めるよう呼びかけることまではできなかったと述懐している[56]。
        """,  # paste Asahi Shimbun disaster-related deaths article here
        "source": "Wikepedia",
        "language": "ja",
        "publish_date": "2024-11-10",
        "event_id": "noto-earthquake-2024-01",
    },
    {
        "title": "能登半島地震 死者241人に 行方不明者なお9人",
        "body": """
            令和6年能登半島地震

            　令和6年（2024年）1月1日、地元へ帰省している方も多かったと思われる元日に、石川県能登地方を大規模な地震が襲いました。強い揺れを伴う地震が何度も発生し、家屋倒壊や土砂崩れが各地で発生したほか、沿岸各地に津波が襲来しました。この地震により死者241人、全壊家屋8,027棟など甚大な被害※1が生じました。また、この地震は、国土地理院の観測により輪島市西部で最大４m程度の地面の隆起が検出されるなど、陸域直下で発生した地震としては近年まれにみる大きな地震でした。

            ※1 令和６年３月５日14時00分現在、消防庁災害対策本部資料による。

            震度分布

            （1）一連の地震活動

            　令和6年（2024年）1月1日16時10分、石川県能登地方の深さ16kmでマグニチュード（M）7.6の地震（最大震度７）が発生しました。この地震によって、石川県輪島市及び志賀町で震度7を観測するとともに、能登地方の広い範囲で震度6弱以上の非常に強い揺れとなったほか、北陸地方を中心に北海道から九州地方にかけて震度6弱から1の揺れを観測しました。また、石川県では長周期地震動階級4を観測したほか、北陸地方を中心に東北地方から中国・四国地方にかけて長周期地震動階級3から1を観測しました。

            地震活動

            　この地震に伴い津波も発生しました。沿岸域で発生した地震だったため、地震発生から短時間で津波が襲来するとともに、日本海という閉じた海域で津波が反射を繰り返し、長時間継続しました。津波の高さは、石川県金沢市や山形県酒田市※2で80cmを観測するなど、日本海沿岸を中心に北海道から九州地方にかけての広い範囲で津波を観測したほか、後日の現地調査により新潟県上越市で5.8m（遡上高、速報値）などの津波の痕跡を確認しました。

            ※2 巨大津波観測計による観測のため、観測単位は0.1m

            　石川県能登地方では、この地震の発生よりも前から、地震活動が活発になっていました。一連の活発な地震活動は令和2年（2020年）12月からみられており、令和5年（2023年）5月5日にはM6.5（最大震度6強）の地震が発生、以降、活動がさらに活発化している状況の中で、１月１日の地震が発生しています。地震の規模や顕著な被害を踏まえて、気象庁では地震活動の名称を「令和6年能登半島地震」と定めました。この名称は、令和6年（2024年）1月1日に石川県能登地方で発生したM7.6の地震のみならず、前述の令和2年12月以降の一連の地震活動を指しています。

            　再び１月１日16時10分の地震に目を向けて、その地震の発生直前に着目すると、地震の震央周辺ではM7.6の地震の約4分前の16時06分にM5.5の地震（最大震度5強）が発生していました。また、M7.6の地震発生以降、1ヶ月の間に最大震度5弱以上の地震が17回発生するなど活発な地震活動が継続しました。地震活動の範囲は、令和5年12月までは能登半島北東部の概ね30km四方の範囲でしたが、1月1日の地震の直後から能登半島及びその北東側の海域にも広がり、北東－南西方向に150km程度もの範囲となっています。この地震活動の分布や地殻変動解析などから、1月1日のM7.6の地震の震源断層は、北東－南西方向に延びる150km程度の長大な長さを持ち、能登半島の陸域直下にも推定されています。また、能登半島沿岸部の活断層が活動したことが地震調査委員会により推定されています。

            　1月1日以降の地震活動は、過去に内陸及び沿岸で発生した主な地震の地震回数と比較しても非常に活発で、「平成16年（2004年）新潟県中越地震」や「平成28年（2016年）熊本地震」よりも多くなっています。

            気象庁記者会見の様子
            内陸及び沿岸で発生した主な地震の地震回数比較（M3.5以上）

            （2）緊急地震速報や津波警報等の発表

            　気象庁では、1月1日16時10分に発生したM7.6の地震において、直前（十数秒前）に発生した地震と合わせ、石川県能登地方に対して緊急地震速報（警報）を発表し、その後予測の更新に合わせてより広い範囲に対して緊急地震速報（警報）の続報を発表しました。また、令和6年1月の1か月間にこの地震を含む一連の地震活動のうち、20個の地震に対して緊急地震速報（警報）を発表しました。緊急地震速報の発表状況からも、いかに活発な地震活動であったかが分かります。

            　津波警報等の発表状況としては、1月1日16時10分の地震に伴い、16時12分に新潟県、富山県及び石川県に津波警報を、北海道日本海沿岸南部から山口県にかけての日本海沿岸に津波注意報を発表しました。その後、16時22分に石川県能登を大津波警報に切り替え、山形県、福井県及び兵庫県北部を津波警報に切り替え、北海道太平洋沿岸西部、北海道日本海沿岸北部及び九州地方の日本海沿岸に津波注意報を発表して、警戒を呼びかけました（2日10時00分に全て解除）。

            　また、1月1日の地震や津波に対し、複数回記者会見を開いて、津波からの避難や地震活動等について注意・警戒を呼びかけたほか、その後も定期的に報道発表を行い、地震活動の状況や今後の見通しについて解説しました。

            （3）現地調査

            　震度5強以上を観測した地震では、震度観測点の観測環境が地震により異常となっていないかの点検や、震度観測点周辺での被害状況の調査を行うこととしています。このため、気象庁は気象庁機動調査班（JMA-MOT）を派遣し、最大震度７を観測した1月1日16時10分の地震発生以降、震度5強以上を観測した震度観測点（81地点）の設置状況の点検、及び震度観測点周辺（周囲約200m）での被害状況の調査を行いました。その結果、石川県内の震度観測点3地点（七尾市中島町中島、中能登町井田、羽咋市旭町）で観測環境に異常が認められたため、速やかに地震情報への活用を停止するとともに、1日16時10分以降に観測された震度を欠測としました。このように、活発な地震活動が継続する中でも、正確な震度の情報をお伝えできるように努めることも、気象庁の重要な業務です。なお、その他の78地点においては、震度計台や周囲の地盤等には震度観測に影響を与えるような異常は認められませんでした。

            現地調査による津波の痕跡から推定した津波の高さ
            現地調査の様子

            　また、気象庁では、津波観測点付近や津波による顕著な被害があった地点において、津波の痕跡等から津波の高さを推定するための調査も実施しています。その結果、新潟県上越市船見公園では5.8m（遡上高、速報値）の津波による痕跡がみられるなど、津波による浸水の影響を確認しました。

            （4）臨時の津波観測装置の設置

            　今回の地震の影響により、能登半島北部に位置する「輪島港」（国土交通省港湾局所管）及び「珠洲市長橋」（気象庁所管）の両津波観測地点の観測データに欠測が生じました。気象庁は港湾局の協力のもと両津波観測地点に臨時の津波観測装置を設置することとし、「輪島港」については1月8日から、「珠洲市飯田」については2月9日から、津波・潮位の観測・監視を再開しました。

            臨時の津波観測装置の設置作業

            　また、政府の地震調査研究推進本部地震調査委員会における令和6年能登半島地震の評価（2月9日公表）において、令和2年12月以降の一連の地震活動は当分続くと考えられ、能登半島地震の震源域の活動域周辺での津波を伴う地震の発生の可能性があることが指摘されていることを受け、当該地域の津波観測体制を強化するため、「上越市直江津」及び「佐渡市小木」にも新たに臨時の津波観測装置を設置し、津波・潮位の観測・監視を3月27日から開始しました。

            （5）JETT（気象庁防災対応支援チーム）の派遣

            　JETTとは、大規模な災害が発生または予想される場合に、都道府県や市町村の災害対策本部等へ気象庁職員を派遣する取り組みです。派遣された職員は、現場のニーズや各機関の活動状況を踏まえ、気象等のきめ細やかな解説を行い、各機関の防災対応を支援しています。

            　１月１日の地震でも、発災直後から石川県庁や能登半島の被災市町に気象庁職員をJETTとして派遣しました。派遣された職員は、石川県や能登半島の被災市町の災害対策本部で地震活動の状況や気象の見通し等の解説を行うほか、救命救助や復旧活動等を行う各機関から気象情報のニーズを聞き取り、その内容を踏まえた気象状況の解説を行うなど、各機関の防災対応を支援しました。

            気象情報のニーズ把握
            地震活動状況や気象の見通しを解説
            """,  # paste NHK or government mid-February count update here
        "source": "Japan Government",
        "language": "ja",
        "publish_date": "2024-02-16",
        "event_id": "noto-earthquake-2024-01",
    },
]

actions = [
    {
        "_index": INDEX_NAME,
        "_id": f"{doc['source']}-{doc['publish_date']}-{doc['event_id']}".lower().replace(" ", "-"),
        "_source": doc,
    }
    for doc in test_articles
]
success, failed = helpers.bulk(es_client, actions, refresh=True)
print(f"Indexed {success} articles")