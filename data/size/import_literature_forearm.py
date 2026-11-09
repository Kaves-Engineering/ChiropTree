"""Import forearm lengths from the literature for bats whose call is measured
but whose forearm was not, so they can be placed in the call plot.

The call plot (README, "Call plot") needs a measured forearm and a recorded
peak frequency for each species. In November 2026, 101 species had the peak but
no measured forearm in data/chiroptera_body_size.json: the trait databases
either lacked them or held only an estimate (a parent species' value after a
split, or imputation). This importer fills 99 of them, and four more whose calls came in later: Anoura peruana and Sturnira hondurensis (Zamora-Gutierrez et al. 2016), Rhinolophus nippon and Murina ryukyuana (Funakoshi 2010), and four Pteronotus whose calls came from Plazi treatments from published
measurements, transcribed by hand. Two are still open: Molossus bondae (only
the paywalled revision of Loureiro et al. measures it as a species) and Myotis
nipalensis (no open source prints its forearm).

Sources, in the order the card prefers them:

1. A study that measured the bats: a species description or revision, a
   regional inventory, or the call paper itself where it also measured
   forearms (Kofoky 2009, Goodman 2011, Grunwald 2024, Curran 2022, Taylor
   2012, Patterson 2025, Gomeh-Djame 2026). Means are imported as means, with
   SD and n where printed; sexes are kept apart where the source separates
   them. A range printed without a mean is 'range_only'.
2. Handbook of the Mammals of the World, vol. 9, Bats (Wilson & Mittermeier
   2019), used only where no study above covers the species. Each species
   account gives the forearm as a range compiled from the literature, so every
   row is 'range_only' with range_type 'min_max'; build_size.py never lets its
   midpoint into a median beside a real mean.

Most texts were read from Plazi TreatmentBank, which publishes each species
treatment as XML (doi of the HMW deposit: 10.5281/zenodo.6397752 and its
siblings). Plazi's OCR of HMW turns decimal points into hyphens or colons:
"forearm 42-9-49 mm" is 42.9-49 mm, "38.7-42- 1 mm" is 38.7-42.1 mm. Read
by magnitude there is only one way to place the point in each, and every
value below was read that way by hand; the OCR text is kept in
verbatim_value so the reading can be checked. The HMW account of
Hipposideros hypophyllus ("38-49 mm") is not used: the species' own specimens
measure 37.1-40.0 mm, so the printed range is taken as an error and the
2014 specimens are imported instead.

Names: each row names the MDD v2.5 species it belongs to. Where the source
used another name (an older genus, or a species since split), the row is
'manual' and its note says why the bats belong to the MDD species. Rows from
before a split are assigned only where the source's locality lies wholly
inside one daughter's MDD range (Benda & Vallo 2012 for Rhinolophus clivosus
and R. acrotis; Kuo 2017 for Kerivoula depressa); build_size.py still flags
such species as measured before the split.

Raw files (gitignored, checksum-pinned):
- data/raw/<call paper>.pdf|.xml: the copies the call importers already pin;
- data/raw/size/plazi/<docId>.xml: https://tb.plazi.org/GgServer/xml/<docId>
- data/raw/size/literature/: the open PDFs and XML named in RAW_FILES.

Run: uv run data/size/import_literature_forearm.py
"""
from collections import defaultdict

from size_lib import DATA, RAW, SizeResolver, check_raw, number, write_review, write_rows

CALL_RAW = DATA / "raw"
LIT = RAW / "literature"
PLAZI = RAW / "plazi"

RAW_FILES = {
    "kofoky-2009": CALL_RAW / "kofoky-2009.pdf",
    "goodman-2011": CALL_RAW / "goodman-2011.pdf",
    "webala-2019": CALL_RAW / "webala-2019.pdf",
    "grunwald-2024": CALL_RAW / "grunwald-2024.pdf",
    "curran-2022": CALL_RAW / "curran-2022-namuli.pdf",
    "taylor-2012-hildebrandtii": CALL_RAW / "taylor-2012-hildebrandtii.xml",
    "patterson-2025": LIT / "patterson-2025-pmc11776429.xml",
    "benda-vallo-2012": LIT / "benda-vallo-2012.pdf",
    "mamani-contreras-2021": LIT / "mamani-contreras-2021.pdf",
    "srinivasulu-2014": LIT / "srinivasulu-2014.pdf",
}
RAW_SHA256 = {
    "kofoky-2009": "26436d299810e72deb211d725d4c21b501b4de56579d6d43ce17a2d6c2c85c46",
    "goodman-2011": "ca4b95d7675a4a584c64655246ee5e6014257df4bac5c60443f5fcc9f0a8da6d",
    "webala-2019": "a3c130b636d04e87883f801a86f546ce5db4584744688abc4841842fc95c2a15",
    "grunwald-2024": "0168e6a26a1a006a1069707ded5b2163fd06621dff2c34d7df6f984f7c713861",
    "curran-2022": "1fdab54c9da3b41c4118f1f5997a530e91834d0e704fc887a544c2a651d2ed89",
    "taylor-2012-hildebrandtii": "ce9ced903081172ca092759453f6db6f8e0b38ecff15bd65a36a8502468ec3aa",
    "patterson-2025": "557c720df675a2d4b2af6cedbbea0b6e99c49b8172357398ff6669ae34fcc21c",
    "benda-vallo-2012": "e24a3d2fa3238d7ac3e0adb7bb57b3e9a1a3c61393cd233f22cf97f60f80b4ac",
    "mamani-contreras-2021": "1d879318422e5580db0728e17350383536240819ed0f5fa4f8274c68f8fa2d4b",
    "srinivasulu-2014": "595dcf0afb056bf3f0a33e41089164b1119d4ff0490cfc88873e9ec0e0793800",
}
# Plazi treatment XML: docId -> sha256 of the cached copy
PLAZI_SHA256 = {
    "885887A2FFD98A3EF89CEFB2FE0DD1D4": "b34d9a8e3d1d1b5543836f9578a4ded5d453634573f312959704fee433f7c963",
    "194287C9FFA7BA0CB1AFFC50B66EF9EE": "0dbcabb3bb3f06b93362c2ac72d966b8b8793b631c612ed6595b464ef32c4ac9",
    "4C3D87E8FFA16A1EFF429DAD16F3B09B": "0666db2a721498ca5d19986daf1ccd3481e6bd90bebc5c594ff2606814d4cf67",
    "4C3D87E8FF966A29FA8895F51406B2A1": "6c0439b554147d2faaa1ab22c6159aec519e0eeddc3a4d66b4c43ae3f602ec34",
    "4C3D87E8FF716ACEFF4D9EF3167BBA8C": "4c771e76a0093f0715ac8a4703f7c2ee0713f6c64d407606f14f2fe38a44f9ac",
    "885887A2FFE48A02F8B7FC6AF77CC945": "480441a8f10a6466dce1d88ea569ba1913fd08568b19e09428c70982f69ed423",
    "885887A2FFC18A27FF69EFAAF4D0D285": "491b9060b2756c42cd83fcf6b1b49525245b5145f78d55d7dc1fde4db46b1d43",
    "4C3D87E8FF666AD9FF51942A1CC5B288": "f5ec33efb65f260dc9c2782f887b13ceb48b9841aa144ec07a77d863899acad3",
    "4C3D87E8FF9C6A2CFA8F9B521A9FB345": "9809fcdeb9941e76c0685ef7d0c3237e7e46d4b49ccc4571b9c998828e033f3a",
    "4C3D87E8FFA76A18FF51958919CFB8E6": "f2dd00ac829ff3ac20937fefe13b2bc52193ecbc9e1015a970e3734cbff07feb",
    "194287C9FFB6BA1AB495FFF1B59BFE36": "370878b1b264c242c9790fb2deb391cb781572952f82b7ea1628b4ef55048882",
    "860EC8445712FFE9FF03FB05B262F26F": "b73d4e90a246a2a92ca4852aeeaf256c1e21ed8f5e9e3e4590a14ba7b59c5869",
    "03A63743915EFFE2E4E4CDC6284BA4B6": "de58fb5256ea5b78be62e0f0245e4d2612f47b6593b0b7b9f951443e40d0c816",
    "194287C9FF98BA35B16DFFDCB0DFFCC6": "f251d87cc1db42d789a1b7a8d67f2bf305da9f4e4ec4eeaf1b0e328098f6c950",
    "194287C9FF8FBA23B4A6F4A8B608F660": "b067065cb207fc92b2b5abe9a872151283d30653ad911b65bff8a321ca461eea",
    "4C3D87E8FFDB6A64FF4D95171EFAB6B0": "1e9ce16d966889817bb6a7ecaa8f53c24d4c439ef58ea8a267a25f7d016cd903",
    "4C3D87E8FFCB6A75FA519FDC1B23B1DD": "89d7eaa23edfc47c2c339e7a80ac17813284910a87b9ecd8ea6358325a7014b5",
    "4C3D87E8FFAA6A15FF7C9037179ABA50": "12fca7e1295519dea310d7dcdd30e711a78dedd678235ff3bd13448c56a25cca",
    "4C3D87E8FFDA6A65FF849DAE1699B286": "fe35a64b3b10ec20d6c3ed179b490585e2be30226ef5c74a53c6883c340fd103",
    "4C3D87E8FFDA6A66FA8B9FA41A19B22A": "93c1cf1a212e2446ccb537d1e85eedb25f4c0dcdf8647ec69bc38b530d19db2c",
    "4C3D87E8FFD96A66FF539F3819BFBCE8": "96dbc6505ebe54b872e15b0698655bfff9f4734d1cbcbb396e348cff3152599d",
    "4C3D87E8FFE26A5DFF919E4D18B8BFBC": "159ffdeeb9fcdbcd7aa7b690fff34743cefdd030a91396b1843478d502fe59a0",
    "03D587F2FFDA4C11FF723C6DF706FBF5": "ec775987b36575809b134bb4bcfdea6cc0a1ee33e8512c88bef79a70a1f47e78",
    "03D587F2FFDB4C10FF04395FF587FB05": "74263889a21a0d11514892307985a8a0aa8de68c19624d3e9e7ab1d0866f6389",
    "4C3D87E8FF9D6A22FF4E9A1419C2BE0C": "4922d11b8ea20cf12f44903b6b40f397e10cdf7071555a53decb85758b31b334",
    "4C3D87E8FFAF6A10FA5394D718F1B3DB": "510782b8e3fc97ff5e14b83fa0cb7c347973a78cd250ed93141b365a46b6bf64",
    "4C3D87E8FF9E6A21FF81941A1F8AB00E": "7f6ecf08ee4a08dd9256921dcff31543a76c744430ac8fd1b6728e5973056e9c",
    "4C3D87E8FFAD6A13FA489C2A1F41BF8C": "a80b69e8a5b772ba190cef4d762ab293e7ae97d2dbe907da0a992b96a7251166",
    "03D587F2FFCA4C01FF7431D4F8DBF2F5": "a5e41ffb7ec8d428716ec622534f90984a5c8aa5ab95ceae8a5558cde1c2590c",
    "194287C9FF93BA20B1BEF06EB11EFD9F": "830fd6a243fabdb41da22c1d2a4b4b2b6b8a4c6849e6faa95d592198570ed2e5",
    "4C3D87E8FF6F6AD1FA91909E1B63BDB7": "23c7f3ddf40496d4e7f5a406652f340a97bb0aab438046966f55e56d28fee899",
    "4C3D87E8FF2F6A90FF51975E1FA4B225": "e3c6a49f09bd334fcdd50139ca626204459d8efc92fa53b83f7dd8f3e03745f6",
    "4C3D87E8FF2B6A94FF5296A61F61B0CE": "2bb76fe655e33fad47c8dd64b72adaf91783d7768b53d1bce3f257a4e5da3374",
    "4C3D87E8FF346A8BFA82932516A6B6B5": "80b9bf3e7ba03bfd7ba4cea4f2f24f846fa558528683e4317841c40b9d582354",
    "4C3D87E8FFBF6A01FA569C0B1D3FBF02": "aa09d0a0fc0ca525caba8f58c0f5770570bae0770b8e3bcda6901ddba99d6325",
    "4C3D87E8FF7E6AC1FF409D3B184EBC70": "3beb41a9f4137f6dc0230e816181b27584da5ba95e6cdfb6ba3a16142227009a",
    "4C3D87E8FFFD6A43FA4E952F1D9FBCA2": "d059d3463d8f46d18de3765f08be389b7dc1d5716b674898f59cee9d64f5151b",
    "4C3D87E8FFE26A5DFA9692811886B695": "b1843431d9c91aa9d52ba418cd46463110a359b28fa55b7bd3f9efd7d5a420c4",
    "4C3D87E8FFC36A7DFA4D9B571DD0B205": "4a6065c087fa28560cbc75469ad568e4dc2f571165afd3a03ae8e3d350d03b23",
    "4C3D87E8FF396A87FA489C2A1B2FB322": "255e1b1cf1c075c2d5d6475a1dc3eac7dadb1912a2cbebe3e4616e2f57b377ef",
    "4C3D87E8FFCF6A71FA599B521DE4B2B7": "16ee01daa924f903d2dd28e6b9758262a8992351150c74cf023b66305604c6a6",
    "E84887F9FFD4D65A0AC8FE4618BD3100": "0a6d2057ce7dcffd4c25991378f5f6b7038181138785a3a212a8390577984827",
    "4C3D87E8FF316A8FFA5190A81FC6B95B": "0ec6c9499aa75c0ffc7741cc8d2f7d061736ef1c97e869a9b498dea239cf9ccd",
    "E84887F9FFD5D65B0FE6FE1B1B4A3CF7": "deec57e0b7023a5a7a9f6a63f9436f24027a877fd77f35102b2dc476b3f8c981",
    "885887A2FFD98A3FF887FCC8F71ED6C6": "61f657c1922f6272abf6a7251753182d10b0c7137117e511921a87bdc234e7d1",
    "4C3D87E8FF936A2CFA4C92B81462B74B": "755c55e2a2acd01a86ecbfe1a00bc68c5fdbb7556693773809655d16431dd685",
    "194287C9FF8CBA20B482F5FEB6BEF840": "048df878899ce8f796c0a4e7aac39d3e194f92471edc023e0e5b4890238a31c0",
    "4C3D87E8FF466AFAFA8E9A951D07B3C5": "25ece932021b3f0a258325d7f03f0c63c91deced31ec4ac423e78e9de18d449a",
    "4C3D87E8FFE76A59FF579A181D28BF49": "57ed3ac07edf306655293e3bbd95d7f9916d23005b988d7e56f662b2bca8c78d",
    "03BD87A2C678A20AFF4AF83BFC745253": "1836f853929c616a01c307f1a0529fa01bded57908479535d71eb1a44202104d",
    "4C3D87E8FFE36A5DFA4F90F71DBEBAFA": "96035771b4747f9016dc31f2381cc8be97c570a75c0cb9a6795f4fba63a8ca64",
    "03BD87A2C67AA208FF57FB47FB1E4E1A": "59513b509a5ed2536fc619699b64cc977171a54d6d2d6175b437cfbf6a8b6566",
    "4C3D87E8FF836A3CFF53975F1F8EB778": "2a3c557d094b483e4fdb859e8bb1271bec08d187f24f6d9ff6329bb00fb53e00",
    "4C3D87E8FF586AE0FA869DA11A47B283": "9455f79213bd49ba842294ea78080f2773d94d429d953023e0967365fc9ca54f",
    "885887A2FFFE8A1BF8B4EFE6FC7FC876": "92999932ac0eceebd1cdf1225fc07d4438f87a82f35566870d4b47fdb76ed6a1",
    "03B7D66B3A3AA1439FD2F9AC6629F91A": "22e4dcb59f795f0a9a516c86d89535231b0c3fff775e88a4c683ee264d2955b7",
    "E83187852A6D416DFF18FF657B6FF861": "e0bd6e328932e33343ff49e6054f0f26ae1969a9d8b0110165f824720690e26c",
    "6A61B42FFF8DFF8A84D3FB3EFAEDF841": "bdd2cb9cd55e8e17e479b6fafade9a05235508926da4c130de62417561667c5f",
    "8152915BC2253768FEF5B577FC85FB3E": "684a92a47f72eaadde34b8d09b9f3b18d4eb1a6a1472aa9c7a3909f2f3130e7c",
    "03AF87D3C435B542FF728049FB55BB1B": "55a14e79f9c269d5859bcaa3c7509b109073f171adcb9151f91b55863e2de93b",
    "2431452B35609A3CFC71C70BA93CFE5F": "1e599497a91cac7f5dc04af4274a4d2bdbbe5ee610a02a502dcde8745422e3bf",
    "2431452B35609A3DFC73C0B7AC8FFE54": "7c852dc1bc9009e95fe3ea3f9229307e15ae0da7f917a6331dc9260a51b2a534",
    "2431452B35609A3DFC9AC3EFAC63FA81": "df51683b0d97760d061fced645334f3e03223f98a377b17f19f164acb097925e",
    "2431452B35619A3CFF09C410A961F855": "a437ecc7d4ff1fb3f7f8f905289a0e1488790944c422b7eca84acfbde6a15405",
    "2431452B35659A38FEC5C700AD5AFC16": "8feeefa3e112cf49fd577d83e16ddc760bfe3adebfb8b9ba63bba020b8c289b5",
    "35434B4BD644FF91FC68FEF08591A3A5": "130b6bd5e1a5a0511b2ad2946ac345dbcd9eaea1a8b371d66dacaaa5176a5f4e",
    "4D413F2D0F2E9E3BFF2FF8E268E94B67": "b74163da9e6ff4cbe7dc26603d5e71befc633e5d81fd2865f397f1dd16801034",
    "5A962FACC19045F5C14DCC83757176E5": "d4fd44345f9d82106f1cbc497aff6653fa88db85a2266353b5cc26dd0e7877a9",
    "646A3D65FFC4FF8B7C94685BB44EAB56": "df7f77968530a872da9f8a75a812ca998be8fb19d44197801a24288c22108933",
    "9F07878AA866CD601888DE649C175E02": "a99b212d12d512e0f5c28bb81b3722ac6aa218e4760ee638cd98f224c116ef32",
    "AB148783FFFA3B3EFF43A10CFE85FD81": "085341ca2d641545c2ea896914e77436bb2d7480ca6df8efb752002214c41a61",
    "C5AF2404F3885C65BBB578DA25C08937": "37d9cc84d8fea940872e51dd0895a2d98bfcc5d8c65e7cf9faf10c3ac6d1c2a8",
    "039C87D8204FFFD4FF5EFBF7FDCCA855": "f7f647a239ef4a8fc863f530c3a4e8fa6c71b993ad3bf1f71784ef24e109d9b9",
    "03B6EE58FFAC4F7DFC861F8EA30AFC4F": "2b8124414188b1682a4c386c77fdc9692ad5d1bbeb0fea6b403c766cd4d95c03",
    "03BB87E9FFFB2D36FF6DF985FD32FC61": "eebfc087e5ef54442be86edc885ae63963079785db3c62149d743fa7ef286bc2",
    "03BB87E9FFFF2D3AFF6DFC27FBE4FE04": "b9aa0ae584b44d563e82de0f62399d86f21b596691aa17e1b6a07448e8cd031a",
    "03BB87E9FFF12D3EFF6DF8A7FEDAF914": "43b129082295da39af06b18a60761ad4e7f1dc5b789f18630977278bfe85ea9f",
    "1320879DFFB3FF9AFC34FC6E6952F86C": "e131bde38fabb1ab1ae14dcf3a26e03535bd5beae459ae154468823cc59d2dd7",
    "03B03903A3472524BD98FA0346ACF9E7": "1a887a264bfea31346918558fa5dbd37dc401cc37d34244b5776b3f897d40398",
    "03A687BCFF94FF97164EF411FCC7FB49": "56733eb7ffc85046a1dff4702a5b56d0e4b59ae02e5c29bc42f6b30de430748e",
    "885887A2FFDD8A3AF896FB47F94CD195": "2e8592a758cfc62516fea01d047836557ce8966cd44ed5fa1738ed0a125de116",
    "03BB87E9FFE72D33FF6DFA3AFD91FB49": "ebc9336ba3d36889ed542b50087a2f51774e9fc8e7feba6f8f3f07f7d2737cb4",
    "4C3D87E8FF636ADCFF819E1F1D6CB6BB": "b3ee58ba49604e396961f13463ba7d40ddd80176bf1cb2b7a89fb117adc3980a",
    "03A63743915FFFE3E4DFC5BF28E3A80A": "fea2d1f4aa8bff2693edef9ac4b289540e1d17a35bb60919e4428cfe6bc8f95f",
    "03A63743915FFFE2E1DBC1E32DD4A4EE": "fc0e526d0a9f909c83d7ca1a2bb54823835bd3913c64cdf719482576a62e9120",
    "03A637439150FFECE4EACCF02EB6ACD0": "f780a9ac4f7bac8045779d464e122b927e0e0cb712aca9fc9fab651f54e0abf3",
    "46341E41E13EE51BFC495ED1FE4FC1FD": "a4fca9fbba6c9b0000eba7b7c184acc76abe42c23a4e7da2a0c12c920e483bd1",
}

# Publication year (data_year) per source; Webala's rows carry their upstream's.
YEAR = {
    "kofoky-2009": "2009", "goodman-2011": "2011", "webala-2019": "1996", "grunwald-2024": "2024",
    "curran-2022": "2022", "taylor-2012-hildebrandtii": "2012", "patterson-2025": "2025",
    "gomeh-djame-2026-lobeke": "2026", "hmw-2019": "2019", "csorba-2011": "2011", "feijo-2015": "2015",
    "ralph-2015": "2015", "kuo-2017": "2017", "zhang-2009": "2009", "monadjem-2010": "2010",
    "benda-vallo-2012": "2012", "geluso-bogan-2018": "2018", "srinivasulu-2025-hipposideros": "2025",
    "kaur-2014": "2014", "novaes-2022": "2022", "tu-2017": "2017", "medina-2014": "2014",
    "vannatta-2021": "2021", "benda-2024": "2024", "saikia-2025": "2025", "loureiro-2018": "2018",
    "mamani-contreras-2021": "2021", "srinivasulu-2014": "2014", "hernandez-canchola-2021": "2021",
    "colombo-2018-pteronotus": "2018",
}

# One row per printed record:
# (reference_id, raw key (RAW_FILES key or Plazi docId), MDD species, name as printed,
#  locator, sex, statistic, value, min, max, sd, n, area, verbatim, note, upstream)
# statistic: mean | single | range_only; for range_only, value is left to the
# importer (the midpoint). None = not printed.
M, S, R = "mean", "single", "range_only"
ROWS = [
    # --- call papers that also measured forearms -------------------------------
    ("kofoky-2009", "kofoky-2009", "Paremballonura tiavato", "Emballonura tiavato", "Table 1, FA column", "pooled", M, 38.0, None, None, 0.66, 6, "Madagascar", "38.0 ± 0.66", "Emballonura tiavato is now Paremballonura tiavato (MDD)."),
    ("kofoky-2009", "kofoky-2009", "Laephotis malagasyensis", "Neoromicia malagasyensis", "Table 1, FA column", "pooled", M, 30.7, None, None, 1.15, 6, "Madagascar", "30.7 ± 1.15", "Neoromicia malagasyensis is now Laephotis malagasyensis (MDD)."),
    ("kofoky-2009", "kofoky-2009", "Scotophilus tandrefana", "S. tandrefana", "Table 1, FA column", "pooled", S, 46.2, None, None, None, 1, "Madagascar", "46.2 ± 0.00", "One bat."),
    ("kofoky-2009", "kofoky-2009", "Scotophilus marovaza", "S. marovaza", "Table 1, FA column", "pooled", M, 43.5, None, None, 1.33, 9, "Madagascar", "43.5 ± 1.33", ""),
    ("kofoky-2009", "kofoky-2009", "Miniopterus gleni", "M. gleni", "Table 1, FA column", "pooled", M, 47.6, None, None, 1.10, 7, "Madagascar", "47.6 ± 1.10", ""),
    ("goodman-2011", "goodman-2011", "Miniopterus egeri", "M. egeri", "Table 5, 'Across range' row", "pooled", M, 38.5, 37, 40, 0.73, 15, "eastern Madagascar", "38.5 ± 0.73, 37–40, n=15", ""),
    ("goodman-2011", "goodman-2011", "Miniopterus petersoni", "M. petersoni", "Table 5, 'Southeastern Madagascar' row", "pooled", M, 40.0, 39, 41, 0.70, 14, "southeastern Madagascar", "40.0 ± 0.70, 39–41, n=14", ""),
    ("webala-2019", "webala-2019", "Macronycteris gigas", "M. gigas", "Table 3, Shimoni female row", "female", M, 109.2, None, None, 2.5, 43, "Shimoni caves, coastal Kenya", "109.2+2.5 (n = 43)", "Webala et al. took these from Guillén-Servent (1996), who compiled them from earlier studies."),
    ("webala-2019", "webala-2019", "Macronycteris gigas", "M. gigas", "Table 3, Similani male row 1", "male", M, 116.1, None, None, 2.6, 69, "Similani caves, coastal Kenya", "116.1+2.6 (n = 69)", "As above, via Guillén-Servent (1996)."),
    ("webala-2019", "webala-2019", "Macronycteris gigas", "M. gigas", "Table 3, Similani male row 2", "male", M, 116.4, None, None, 2.4, 11, "Similani caves, coastal Kenya", "116.4+2.4 (n = 11)", "As above, via Guillén-Servent (1996)."),
    ("webala-2019", "webala-2019", "Macronycteris vittata", "M. vittata", "Table 3, female row 1", "female", M, 93.0, None, None, 2.3, 59, "Shimoni and Similani caves, coastal Kenya", "93.0+2.3 (n = 59)", "Printed as H. commersoni in the original studies; mainland African populations are M. vittata. Via Guillén-Servent (1996)."),
    ("webala-2019", "webala-2019", "Macronycteris vittata", "M. vittata", "Table 3, male row 1", "male", M, 101.8, None, None, 2.2, 80, "Shimoni and Similani caves, coastal Kenya", "101.8+2.2 (n = 80)", "As above."),
    ("webala-2019", "webala-2019", "Macronycteris vittata", "M. vittata", "Table 3, female row 2", "female", M, 90.9, None, None, 2.0, 68, "Shimoni and Similani caves, coastal Kenya", "90.9+2.0 (n = 68)", "As above."),
    ("webala-2019", "webala-2019", "Macronycteris vittata", "M. vittata", "Table 3, male row 2", "male", M, 99.1, None, None, 2.8, 73, "Shimoni and Similani caves, coastal Kenya", "99.1+2.8 (n = 73)", "As above."),
    ("grunwald-2024", "grunwald-2024", "Macronycteris gigas", "Macronycteris gigas", "Table 2, p. 280", "pooled", M, 105.6, 104, 110, 2.4, 7, "Mbam Minkom Massif, Cameroon", "105.6 ± 2.4, 104–110 (7)", ""),
    ("grunwald-2024", "grunwald-2024", "Pseudoromicia roseveari", "P. roseveari", "Table 2, p. 280", "pooled", M, 36.51, None, None, 0.05, 2, "Mbam Minkom Massif, Cameroon", "36.51 ± 0.05, 36.5–36.5 (2)", "The printed range is rounded to 36.5–36.5, below its own mean, so only the mean and SD are kept."),
    ("grunwald-2024", "grunwald-2024", "Pseudoromicia mbamminkom", "Pseudoromicia mbamminkom", "Table 2, p. 280", "pooled", M, 35.42, 34.7, 35.6, 0.56, 3, "Mbam Minkom Massif, Cameroon", "35.42 ± 0.56, 34.7–35.6 (3)", "The type series."),
    ("grunwald-2024", "grunwald-2024", "Afropipistrellus happoldorum", "N. happoldorum", "Table 2, p. 280", "pooled", M, 34.97, 34.8, 35.2, 0.20, 4, "Mbam Minkom Massif, Cameroon", "34.97 ± 0.20, 34.8–35.2 (4)", "Printed as Nycticeinops happoldorum; MDD places it in Afropipistrellus."),
    ("curran-2022", "curran-2022", "Rhinolophus namuli", "R. namuli sp. nov.", "Table 3, p. 31", "pooled", M, 48.3, 47.3, 49.5, None, 5, "Mount Namuli, Mozambique", "Mean 48.3, range 47.3–49.5", "The type series of five."),
    ("taylor-2012-hildebrandtii", "taylor-2012-hildebrandtii", "Rhinolophus cohenae", "cohenae sp. nov", "Table 3, FL column", "pooled", M, 66.4, 66, 68, None, 10, "Mpumalanga, South Africa", "66.4; 66–68 (10)", ""),
    ("taylor-2012-hildebrandtii", "taylor-2012-hildebrandtii", "Rhinolophus smithersi", "smithersi sp. nov.", "Table 3, FL column", "pooled", M, 62.6, 61, 64, None, 5, "Pafuri, South Africa, and Lutope-Ngolangola, Zimbabwe", "62.6; 61–64 (5)", ""),
    ("taylor-2012-hildebrandtii", "taylor-2012-hildebrandtii", "Rhinolophus mossambicus", "mossambicus sp. nov.", "Table 3, FL column", "pooled", M, 62.8, 60, 65, None, 5, "Mozambique and NW Zimbabwe", "62.8; 60–65 (5)", ""),
    ("patterson-2025", "patterson-2025", "Rhinolophus lobatus", "R. lobatus", "Table 2, Forearm length (FA)", "pooled", M, 45.4, 45, 46, 0.55, 5, "", "45.4 (5) 0.55, 45 to 46", "R. lobatus as restricted in this paper, without R. webalai."),
    ("patterson-2025", "patterson-2025", "Rhinolophus webalai", "R. sp. nov.", "Table 2, Forearm length (FA)", "pooled", M, 45.03, 42.7, 49, 1.14, 128, "", "45.03 (128) 1.14, 42.7 to 49", "Described in this paper as Rhinolophus webalai."),
    ("gomeh-djame-2026-lobeke", "C5AF2404F3885C65BBB578DA25C08937", "Glauconycteris lobeke", "Glauconycteris lobeke sp. nov.", "Diagnosis, p. 161 (Tables 1-3)", "pooled", M, 35.85, 35.8, 35.9, None, 2, "SE Cameroon", "FA: 35.8, 35.9 mm", "The two specimens of the type series; the value is their mean."),
    # --- descriptions, revisions and inventories ------------------------------
    ("csorba-2011", "03B7D66B3A3AA1439FD2F9AC6629F91A", "Glischropus bucephalus", "G. bucephalus n. sp.", "Table 1, p. 42", "pooled", M, 34.1, 32.1, 35.7, 0.99, 14, "Indochina", "FA 32.1–35.7 (14) 34.1 ± 0.99", ""),
    ("feijo-2015", "E83187852A6D416DFF18FF657B6FF861", "Histiotus diaphanopterus", "Histiotus diaphanopterus", "Table 3, p. 414", "pooled", M, 45.1, 41.8, 47.2, 1.46, 12, "NE Brazil", "FL 45.1±1.46; 41.8–47.2 (12)", "The type series."),
    ("ralph-2015", "6A61B42FFF8DFF8A84D3FB3EFAEDF841", "Otomops harrisoni", "O. harrisoni sp. nov.", "Diagnosis, p. 18", "male", M, 70.7, 64.0, 74.0, 1.91, 41, "NE Africa and Yemen", "70.7 ± 1.91 mm (64.0–74.0 mm, n = 41)", ""),
    ("ralph-2015", "6A61B42FFF8DFF8A84D3FB3EFAEDF841", "Otomops harrisoni", "O. harrisoni sp. nov.", "Diagnosis, p. 18", "female", M, 69.5, 65.7, 72.7, 1.62, None, "NE Africa and Yemen", "69.5 ± 1.62 mm (65.7–72.7 mm, n = 38)", "The paper prints this female sample as n = 38 in one sentence and n = 22 in another, so n is left blank."),
    ("ralph-2015", "6A61B42FFF8DFF8A84D3FB3EFAEDF841", "Otomops madagascariensis", "O. madagascariensis", "Diagnosis of O. harrisoni, p. 18", "male", M, 63.2, 60.0, 66.0, 1.35, 20, "Madagascar", "63.2 ± 1.35 mm (60.0–66.0 mm, n = 20 males)", ""),
    ("ralph-2015", "6A61B42FFF8DFF8A84D3FB3EFAEDF841", "Otomops madagascariensis", "O. madagascariensis", "Diagnosis of O. harrisoni, p. 18", "female", M, 61.2, 60.0, 64.0, 1.32, 18, "Madagascar", "61.2 ± 1.32 mm (60.0–64.0 mm, n = 18 females)", ""),
    ("kuo-2017", "8152915BC2253768FEF5B577FC85FB3E", "Kerivoula furva", "K. furva sp. n.", "Description, p. 27 (Tables 1 and 2)", "pooled", R, None, 30.9, 37.5, None, None, "Taiwan, India and Myanmar", "forearm length of 30.9–37.5 mm", "Live bats and museum specimens together."),
    ("kuo-2017", "8152915BC2253768FEF5B577FC85FB3E", "Kerivoula depressa", "K. depressa", "Table 2", "female", R, None, 31.2, 34.2, None, 7, "", "♀♀ (7) 31.2–34.2", "Specimens re-identified as K. depressa in this revision, which split it from K. hardwickii."),
    ("kuo-2017", "8152915BC2253768FEF5B577FC85FB3E", "Kerivoula depressa", "K. depressa", "Table 2", "male", R, None, 30.4, 33.2, None, 7, "", "♂♂ (7) 30.4–33.2", "As above."),
    ("zhang-2009", "03AF87D3C435B542FF728049FB55BB1B", "Rhinolophus sinicus", "Rhinolophus sinicus", "Species account, p. 80", "male", M, 46.9, None, None, 1.5, 37, "SE China", "♂♂ : 46.9 ± 1.5, n = 37", "Measured before R. septentrionalis was split off (2017); that species is far larger, so these bats are R. sinicus as now defined."),
    ("zhang-2009", "03AF87D3C435B542FF728049FB55BB1B", "Rhinolophus sinicus", "Rhinolophus sinicus", "Species account, p. 80", "female", M, 46.6, None, None, 2.0, 29, "SE China", "♀♀ : 46.6 ± 2.0, n = 29", "As above."),
    ("monadjem-2010", "2431452B35659A38FEC5C700AD5AFC16", "Triaenops afer", "Triaenops afer", "Field measurements, p. 381", "male", M, 54.1, 51.7, 55.8, 1.18, 16, "Mozambique", "54.1 ± 1.18 (51.7–55.8, 16)", ""),
    ("monadjem-2010", "2431452B35659A38FEC5C700AD5AFC16", "Triaenops afer", "Triaenops afer", "Field measurements, p. 381", "female", M, 52.4, 49.8, 55.2, 1.34, 16, "Mozambique", "52.4 ± 1.34 (49.8–55.2, 16)", ""),
    ("monadjem-2010", "2431452B35609A3CFC71C70BA93CFE5F", "Scotophilus dinganii", "Scotophilus dinganii", "Field measurements, p. 385", "male", M, 52.7, 50.2, 56.6, 2.21, 7, "Mozambique", "52.7 ± 2.21 (50.2–56.6, 7)", "Scotophilus colias, split off in 2015, lives in NE Africa, outside Mozambique."),
    ("monadjem-2010", "2431452B35609A3CFC71C70BA93CFE5F", "Scotophilus dinganii", "Scotophilus dinganii", "Field measurements, p. 385", "female", M, 53.4, 50.3, 57.2, 1.99, 18, "Mozambique", "53.4 ± 1.99 (50.3–57.2, 18)", "As above."),
    ("monadjem-2010", "2431452B35619A3CFF09C410A961F855", "Scotophilus viridis", "Scotophilus viridis", "Field measurements, p. 385", "male", M, 46.4, 44.1, 48.2, 1.22, 17, "Mozambique", "46.4 ± 1.22 (44.1–48.2, 17)", ""),
    ("monadjem-2010", "2431452B35619A3CFF09C410A961F855", "Scotophilus viridis", "Scotophilus viridis", "Field measurements, p. 385", "female", M, 47.7, 45.4, 51.7, 2.06, 8, "Mozambique", "47.7 ± 2.06 (45.4–51.7, 8)", ""),
    ("monadjem-2010", "2431452B35609A3DFC73C0B7AC8FFE54", "Neoromicia zuluensis", "Neoromicia zuluensis", "Field measurements, p. 371", "male", M, 30.6, 29.7, 31.9, 1.15, 3, "Mozambique", "30.6 ± 1.15 (29.7–31.9, 3)", ""),
    ("monadjem-2010", "2431452B35609A3DFC73C0B7AC8FFE54", "Neoromicia zuluensis", "Neoromicia zuluensis", "Field measurements, p. 371", "female", M, 30.0, 28.8, 31.2, 1.18, 4, "Mozambique", "30.0 ± 1.18 (28.8–31.2, 4)", ""),
    ("monadjem-2010", "2431452B35609A3DFC9AC3EFAC63FA81", "Pipistrellus hesperidus", "Pipistrellus hesperidus", "Field measurements, p. 371", "male", M, 30.9, 29.8, 31.8, 1.03, 3, "Mozambique", "30.9 ± 1.03 (29.8–31.8, 3)", ""),
    ("monadjem-2010", "2431452B35609A3DFC9AC3EFAC63FA81", "Pipistrellus hesperidus", "Pipistrellus hesperidus", "Field measurements, p. 371", "female", M, 31.5, 31.3, 31.6, None, 2, "Mozambique", "31.5 (31.3–31.6, 2)", ""),
    ("benda-vallo-2012", "benda-vallo-2012", "Rhinolophus clivosus", "Rhinolophus clivosus s.l. (Holy Land)", "Table 1, LAt, p. 74", "pooled", M, 48.71, 46.7, 49.9, 1.288, 7, "Holy Land", "7 48.71 46.7 49.9 1.288", "Inside the range MDD gives R. clivosus after R. acrotis was split off (2024)."),
    ("benda-vallo-2012", "benda-vallo-2012", "Rhinolophus clivosus", "Rhinolophus clivosus s.l. (Egypt)", "Table 1, LAt, p. 74", "pooled", M, 47.32, 44.0, 49.1, 1.245, 30, "Egypt", "30 47.32 44.0 49.1 1.245", "As above."),
    ("benda-vallo-2012", "benda-vallo-2012", "Rhinolophus clivosus", "Rhinolophus clivosus s.l. (Algeria)", "Table 1, LAt, p. 74", "pooled", M, 45.50, 45.0, 46.0, 0.707, 2, "Algeria", "2 45.50 45.0 46.0 0.707", "As above."),
    ("benda-vallo-2012", "benda-vallo-2012", "Rhinolophus clivosus", "Rhinolophus clivosus s.l. (South Arabia)", "Table 1 (continued), LAt, p. 74", "pooled", M, 49.55, 47.2, 52.2, 1.249, 37, "South Arabia", "37 49.55 47.2 52.2 1.249", "As above. The Cyrenaica sample is R. horaceki, described in this paper, and is not used."),
    ("benda-vallo-2012", "benda-vallo-2012", "Rhinolophus acrotis", "Rhinolophus clivosus s.l. (Ethiopia)", "Table 1 (continued), LAt, p. 74", "pooled", M, 50.24, 44.6, 53.2, 3.092, 13, "Ethiopia", "13 50.24 44.6 53.2 3.092", "Ethiopia and East Africa lie inside the range MDD gives R. acrotis, split from R. clivosus in 2024. The South African sample is not used: R. cervenyi also lives there."),
    ("benda-vallo-2012", "benda-vallo-2012", "Rhinolophus acrotis", "Rhinolophus clivosus s.l. (East Africa)", "Table 1 (continued), LAt, p. 74", "pooled", M, 54.83, 52.5, 56.7, 1.323, 12, "East Africa", "12 54.83 52.5 56.7 1.323", "As above."),
    ("geluso-bogan-2018", "35434B4BD644FF91FC68FEF08591A3A5", "Myotis septentrionalis", "Myotis septentrionalis", "Species account, p. 9", "male", M, 35.4, 33.5, 38, None, 25, "Bear Lodge Mountains, NE Wyoming", "35.4 mm (range 33.5–38 mm, n = 25)", ""),
    ("geluso-bogan-2018", "35434B4BD644FF91FC68FEF08591A3A5", "Myotis septentrionalis", "Myotis septentrionalis", "Species account, p. 9", "female", M, 36.3, 34, 39, None, 35, "Bear Lodge Mountains, NE Wyoming", "36.3 mm (range 34–39 mm, n = 35)", ""),
    ("srinivasulu-2025-hipposideros", "4D413F2D0F2E9E3BFF2FF8E268E94B67", "Hipposideros brachyotus", "Hipposideros brachyotus", "External characters, p. 517", "pooled", M, 47.17, 45.6, 49.6, 1.33, None, "India", "47.17 ± 1.33 mm (45.6–49.6 mm)", "Revalidated from H. galeritus in this paper."),
    ("kaur-2014", "5A962FACC19045F5C14DCC83757176E5", "Hipposideros durgadasi", "Hipposideros durgadasi", "External characters (Table 1)", "pooled", R, None, 34.45, 35.95, None, None, "Karnataka, India", "34.45-35.95mm", ""),
    ("srinivasulu-2014", "srinivasulu-2014", "Hipposideros hypophyllus", "Hipposideros hypophyllus", "Table 1 and description, p. 6494", "male", M, 39.875, 39.86, 39.89, None, 2, "Hanumanhalli, Kolar, Karnataka, India", "39.86, 39.89", "Two voucher males; the value is their mean."),
    ("novaes-2022", "646A3D65FFC4FF8B7C94685BB44EAB56", "Myotis atacamensis", "Myotis atacamensis", "Diagnosis, p. 2", "pooled", R, None, 30.6, 34.1, None, None, "Atacama, Chile and Peru", "FA 30.6–34.1 mm", ""),
    ("tu-2017", "9F07878AA866CD601888DE649C175E02", "Tylonycteris tonkinensis", "T. tonkinensis sp. nov.", "Description, p. 13 (Table 2)", "pooled", R, None, 25.1, 27.8, None, None, "northern Indochina", "forearm length of 25.1–27.8 mm", ""),
    ("medina-2014", "AB148783FFFA3B3EFF43A10CFE85FD81", "Eumops chiribaya", "Eumops chiribaya sp. nov.", "Holotype, p. 27", "female", S, 61.1, None, None, None, 1, "Moquegua, Peru", "forearm length 61.1", "The holotype, the only specimen then known."),
    ("vannatta-2021", "039C87D8204FFFD4FF5EFBF7FDCCA855", "Eumops floridanus", "Eumops floridanus", "Context and content, p. 125", "pooled", R, None, 57.9, 69.2, None, None, "Florida, USA", "longer forearm ( 57.9–69.2 mm )", ""),
    ("benda-2024", "03B6EE58FFAC4F7DFC861F8EA30AFC4F", "Rhinolophus cervenyi", "R. cervenyi sp. n.", "Diagnosis, p. 250", "pooled", R, None, 48, 56, None, None, "Lesotho and South Africa", "Forearm length 48–56 mm", ""),
    ("saikia-2025", "03BB87E9FFFB2D36FF6DF985FD32FC61", "Rhinolophus perniger", "Rhinolophus perniger", "Species account, p. 20", "pooled", M, 71.7, None, None, None, None, "Western Himalayas, India", "average forearm length of 71.7 mm", "Collected specimens; released bats averaged 71.59 mm."),
    ("saikia-2025", "03BB87E9FFE72D33FF6DFA3AFD91FB49", "Rhinolophus nippon", "Rhinolophus nippon", "Species account, p. 16", "pooled", M, 60.5, None, None, None, 4, "Himachal Pradesh, India", "average forearm length of 60.5 mm", "Four bats, two of them old museum specimens."),
    ("saikia-2025", "03BB87E9FFFF2D3AFF6DFC27FBE4FE04", "Barbastella darjelingensis", "Barbastella darjelingensis", "Species account, p. 24", "pooled", R, None, 41.8, 42.9, None, None, "Western Himalayas, India", "41.8–42.9 mm", ""),
    ("saikia-2025", "03BB87E9FFF12D3EFF6DF8A7FEDAF914", "Cnephaeus pachyomus", "Eptesicus pachyomus", "Species account, p. 26", "pooled", R, None, 50.6, 51.2, None, None, "Western Himalayas, India", "50.6–51.2 mm", "Eptesicus pachyomus is now Cnephaeus pachyomus (MDD)."),
    ("loureiro-2018", "1320879DFFB3FF9AFC34FC6E6952F86C", "Molossus coibensis", "Molossus coibensis", "Diagnosis, p. 435 (Table 1)", "male", M, 36.9, 36.1, 37.9, None, None, "", "averaging 36.9 mm (36.1- 37.9) in males", ""),
    ("loureiro-2018", "1320879DFFB3FF9AFC34FC6E6952F86C", "Molossus coibensis", "Molossus coibensis", "Diagnosis, p. 435 (Table 1)", "female", M, 37.0, 34.3, 37.5, None, None, "", "37.0 mm (34.3-37.5) in females", ""),
    ("hernandez-canchola-2021", "03B03903A3472524BD98FA0346ACF9E7", "Sturnira hondurensis", "S. h. hondurensis", "Form and function, p. 23", "pooled", R, None, 43.0, 46.9, None, None, "Honduras and SE Mexico", "forearm length, 43.0–46.9", "Ranges compiled from the literature for the nominate subspecies."),
    ("hernandez-canchola-2021", "03B03903A3472524BD98FA0346ACF9E7", "Sturnira hondurensis", "S. h. occidentalis", "Form and function, p. 23", "pooled", R, None, 38.58, 44.93, None, None, "Sinaloa, Durango and Jalisco, Mexico", "38.58–44.93", "Ranges compiled from the literature for the western subspecies."),
    ("colombo-2018-pteronotus", "46341E41E13EE51BFC495ED1FE4FC1FD", "Pteronotus alitonus", "Pteronotus alitonus", "Morphological description, p. 630", "pooled", R, None, 58.8, 64.5, None, None, "Amazonia", "the FL varies from 58.8 to 64.5 mm", "Range from the type series and López-Baucells et al. (2017)."),
    ("mamani-contreras-2021", "mamani-contreras-2021", "Lasiurus arequipae", "Lasiurus arequipae", "Table 1, CBT 529", "female", S, 47.9, None, None, None, 1, "Lomas de Sama Grande, Tacna, Peru", "FA 47.9", ""),
    ("mamani-contreras-2021", "mamani-contreras-2021", "Lasiurus arequipae", "Lasiurus arequipae", "Table 1, MUSA 21058 (holotype)", "male", S, 46.4, None, None, None, 1, "Huatiapa, Arequipa, Peru", "FA 46.4", "Re-tabulated from Málaga et al. (2020)."),
    ("mamani-contreras-2021", "mamani-contreras-2021", "Lasiurus arequipae", "Lasiurus arequipae", "Table 1, MUSA 21891 (paratype)", "female", S, 47.6, None, None, None, 1, "Huatiapa, Arequipa, Peru", "FA 47.6", "Re-tabulated from Málaga et al. (2020)."),
    ("mamani-contreras-2021", "mamani-contreras-2021", "Lasiurus arequipae", "Lasiurus arequipae", "Table 1, MUSA 21853 (paratype)", "male", S, 46.7, None, None, None, 1, "Chaucalla, Arequipa, Peru", "FA 46.7", "Re-tabulated from Málaga et al. (2020)."),
]

# Handbook of the Mammals of the World 9 (2019): (docId, MDD species, account
# title, page, low, high, OCR text as Plazi has it, note). low == high: a
# single printed value.
HMW = [
    ("885887A2FFD98A3EF89CEFB2FE0DD1D4", "Rhinolophus siamensis", "Rhinolophus siamensis", 301, 36, 41, "forearm 36-41 mm", ""),
    ("194287C9FFA7BA0CB1AFFC50B66EF9EE", "Mops leucogaster", "Chaerephon leucogaster", 646, 33, 37, "forearm 33-37 mm", "Chaerephon leucogaster is now Mops leucogaster (MDD). HMW describes it from Madagascar; MDD also includes mainland African populations."),
    ("4C3D87E8FFA16A1EFF429DAD16F3B09B", "Cnephaeus anatolicus", "Eptesicus anatolicus", 848, 46.1, 50.4, "forearm 46-1-50-4 mm", "Eptesicus anatolicus is now Cnephaeus anatolicus (MDD)."),
    ("4C3D87E8FF966A29FA8895F51406B2A1", "Plecotus ognevi", "Plecotus ognevi", 867, 40, 42, "forearm 40-42 mm", ""),
    ("4C3D87E8FF716ACEFF4D9EF3167BBA8C", "Kerivoula dongduongana", "Kerivoula dongduongana", 898, 30, 33, "forearm 30-33 mm", ""),
    ("885887A2FFE48A02F8B7FC6AF77CC945", "Rhinolophus microglobosus", "Rhinolophus microglobosus", 322, 41.4, 46.3, "forearm 41-4—46- 3 mm", ""),
    ("885887A2FFC18A27FF69EFAAF4D0D285", "Rhinolophus damarensis", "Rhinolophus damarensis", 293, 44, 52.9, "forearm 44-52- 9 mm", ""),
    ("4C3D87E8FF666AD9FF51942A1CC5B288", "Murina peninsularis", "Murina peninsularis", 918, 33.8, 39.4, "forearm 33-8-39- 4 mm", ""),
    ("4C3D87E8FF9C6A2CFA8F9B521A9FB345", "Barbastella darjelingensis", "Barbastella darjelingensis", 861, 38.7, 42.1, "forearm 38.7-42- 1 mm", ""),
    ("4C3D87E8FFA76A18FF51958919CFB8E6", "Cnephaeus pachyomus", "Eptesicus pachyomus", 850, 49, 57, "forearm 49-57 mm", "Eptesicus pachyomus is now Cnephaeus pachyomus (MDD)."),
    ("194287C9FFB6BA1AB495FFF1B59BFE36", "Promops davisoni", "Promops davisoni", 629, 46, 52, "forearm 46-52 mm", ""),
    ("860EC8445712FFE9FF03FB05B262F26F", "Rhinopoma cystops", "Rhinopoma cystops", 176, 50, 67, "forearm 50-67 mm", ""),
    ("03A63743915EFFE2E4E4CDC6284BA4B6", "Pteronotus rubiginosus", "Pteronotus rubiginosus", 443, 61, 67, "forearm 61-67 mm", ""),
    ("194287C9FF98BA35B16DFFDCB0DFFCC6", "Mops niveiventer", "Mops niveiventer", 655, 44, 48, "forearm 44-48 mm", ""),
    ("194287C9FF8FBA23B4A6F4A8B608F660", "Ozimops loriae", "Ozimops loriae", 670, 32, 34, "forearm 32-34 mm", ""),
    ("4C3D87E8FFDB6A64FF4D95171EFAB6B0", "Falsistrellus mackenziei", "Falsistrellus mackenziei", 790, 48, 54, "forearm 48-54 mm", ""),
    ("4C3D87E8FFCB6A75FA519FDC1B23B1DD", "Nyctophilus geoffroyi", "Nyctophilus geoffroyi", 806, 30.6, 41.7, "forearm 30-6—41-7 mm", ""),
    ("4C3D87E8FFAA6A15FF7C9037179ABA50", "Scotorepens orion", "Scotorepens orion", 839, 32.4, 38.8, "forearm 32-4-38-8 mm", ""),
    ("4C3D87E8FFDA6A65FF849DAE1699B286", "Vespadelus caurinus", "Vespadelus caurinus", 791, 26.6, 31.7, "forearm 26-6-31-7 mm", ""),
    ("4C3D87E8FFDA6A66FA8B9FA41A19B22A", "Vespadelus finlaysoni", "Vespadelus finlaysoni", 791, 29.8, 37.6, "forearm 29-8-37-6 mm", ""),
    ("4C3D87E8FFD96A66FF539F3819BFBCE8", "Vespadelus troughtoni", "Vespadelus troughtoni", 792, 30, 36.4, "forearm 30-36-4 mm", ""),
    ("4C3D87E8FFE26A5DFF919E4D18B8BFBC", "Alionoctula westralis", "Pipistrellus westralis", 783, 27.4, 31.3, "forearm 27-4-31-3 mm", "Pipistrellus westralis is now Alionoctula westralis (MDD)."),
    ("03D587F2FFDA4C11FF723C6DF706FBF5", "Centronycteris centralis", "Centronycteris centralis", 370, 42.9, 49, "forearm 42-9-49 mm", ""),
    ("03D587F2FFDB4C10FF04395FF587FB05", "Peropteryx trinitatis", "Peropteryx trinitatis", 369, 36, 43.5, "forearm 36-43.5 mm", ""),
    ("4C3D87E8FF9D6A22FF4E9A1419C2BE0C", "Rhogeessa hussoni", "Rhogeessa hussoni", 860, 30.2, 30.2, "Forearm 30- 2 mm (type specimen)", "The type specimen."),
    ("4C3D87E8FFAF6A10FA5394D718F1B3DB", "Histiotus laephotis", "Histiotus laephotis", 842, 44, 50.1, "forearm 44-50-1 mm", ""),
    ("4C3D87E8FF9E6A21FF81941A1F8AB00E", "Rhogeessa io", "Rhogeessa io", 859, 27.6, 32, "forearm 27- 6-32 mm", "Plazi's metadata titles this treatment Rhogeessa innoxius; its text is the account of R. io (no. 213, Thomas's Yellow Bat)."),
    ("4C3D87E8FFAD6A13FA489C2A1F41BF8C", "Neoeptesicus chiriquinus", "Eptesicus chiriquinus", 844, 42.5, 48.9, "forearm 42-5-48-9 mm", "Eptesicus chiriquinus is now Neoeptesicus chiriquinus (MDD)."),
    ("03D587F2FFCA4C01FF7431D4F8DBF2F5", "Taphozous achates", "Taphozous achates", 354, 59.6, 63.7, "forearm 59-6—63-7 mm", ""),
    ("194287C9FF93BA20B1BEF06EB11EFD9F", "Tadarida insignis", "Tadarida insignis", 666, 57, 65, "forearm 57-65 mm", ""),
    ("4C3D87E8FF6F6AD1FA91909E1B63BDB7", "Murina hilgendorfi", "Murina hilgendorfi", 909, 39.5, 46.2, "forearm 39-5—46- 2 mm", ""),
    ("4C3D87E8FF2F6A90FF51975E1FA4B225", "Myotis fimbriatus", "Myotis fimbriatus", 974, 37, 42.7, "forearm 37-42- 7 mm", ""),
    ("4C3D87E8FF2B6A94FF5296A61F61B0CE", "Myotis macropus", "Myotis macropus", 970, 36, 42.9, "forearm 36-42- 9 mm", ""),
    ("4C3D87E8FF346A8BFA82932516A6B6B5", "Myotis moluccarum", "Myotis moluccarum", 969, 36, 43.1, "forearm 36-43- 1 mm", ""),
    ("4C3D87E8FFBF6A01FA569C0B1D3FBF02", "Arielulus torquatus", "Thainycteris torquatus", 826, 41, 50, "forearm 41-50 mm", "Thainycteris torquatus is now Arielulus torquatus (MDD)."),
    ("4C3D87E8FF7E6AC1FF409D3B184EBC70", "Nycticeius cubanus", "Nycticeius cubanus", 892, 28.6, 32.4, "forearm 28-6— 32- 4 mm", ""),
    ("4C3D87E8FFFD6A43FA4E952F1D9FBCA2", "Nyctalus plancyi", "Nyctalus plancyi", 764, 47, 50, "forearm 47-50 mm", ""),
    ("4C3D87E8FFE26A5DFA9692811886B695", "Alionoctula adamsi", "Pipistrellus adamsi", 783, 29.6, 32.7, "forearm 29-6-32-7 mm", "Pipistrellus adamsi is now Alionoctula adamsi (MDD)."),
    ("4C3D87E8FFC36A7DFA4D9B571DD0B205", "Neoromicia anchietae", "Hypsugo anchieta", 814, 29, 34, "forearm 29-34 mm", "HMW's Hypsugo anchietae is MDD's Neoromicia anchietae, from which N. hlandzeni was split in 2020."),
    ("4C3D87E8FF396A87FA489C2A1B2FB322", "Myotis davidii", "Myotis davidii", 956, 31, 37, "forearm 31-37 mm", ""),
    ("4C3D87E8FFCF6A71FA599B521DE4B2B7", "Hypsugo alashanicus", "Hypsugo alaschanicus", 810, 35, 38, "forearm 35-38 mm", "HMW spells the epithet alaschanicus."),
    ("E84887F9FFD4D65A0AC8FE4618BD3100", "Miniopterus fuliginosus", "Miniopterus fuliginosus", 693, 44.7, 49.6, "forearm 44-7-49-6 mm", ""),
    ("4C3D87E8FF316A8FFA5190A81FC6B95B", "Myotis laniger", "Myotis laniger", 964, 31, 37.1, "forearm 31-37- 1 mm", ""),
    ("E84887F9FFD5D65B0FE6FE1B1B4A3CF7", "Miniopterus medius", "Miniopterus medius", 694, 40, 48.2, "forearm 40-48-2 mm", ""),
    ("885887A2FFD98A3FF887FCC8F71ED6C6", "Rhinolophus episcopus", "Rhinolophus episcopus", 301, 45, 52, "forearm 45-52 mm (subspecies episcopus)", "The nominate subspecies only; HMW gives other ranges for caldwelli (43-45 mm) and an undescribed subspecies (40-46 mm)."),
    ("4C3D87E8FF936A2CFA4C92B81462B74B", "Barbastella beijingensis", "Barbastella beijingensis", 862, 41.1, 46.4, "forearm 41.1-46.4 mm", ""),
    ("194287C9FF8CBA20B482F5FEB6BEF840", "Tadarida latouchei", "Tadarida latouchei", 667, 53, 57, "forearm 53-57 mm", ""),
    ("4C3D87E8FF466AFAFA8E9A951D07B3C5", "Myotis rufoniger", "Myotis rufoniger", 951, 45, 56, "forearm 45-56 mm", ""),
    ("4C3D87E8FFE76A59FF579A181D28BF49", "Tylonycteris fulvida", "Tylonycteris fulvida", 786, 22.9, 27.9, "forearm 22-9-27-9 mm", ""),
    ("03BD87A2C678A20AFF4AF83BFC745253", "Hipposideros demissus", "Hipposideros demissus", 241, 66.9, 66.9, "forearm 66* 9 mm", "A single value."),
    ("4C3D87E8FFE36A5DFA4F90F71DBEBAFA", "Alionoctula angulata", "Pipistrellus angulatus", 782, 31, 37.4, "forearm 31-37-4 mm", "Pipistrellus angulatus is now Alionoctula angulata (MDD)."),
    ("03BD87A2C67AA208FF57FB47FB1E4E1A", "Hipposideros grandis", "Hipposideros grandis", 239, 59, 62, "forearm 59-62 mm", ""),
    ("4C3D87E8FF836A3CFF53975F1F8EB778", "Lasiurus seminolus", "Lasiurus seminolus", 878, 39, 47, "forearm 39-47 mm", ""),
    ("4C3D87E8FF586AE0FA869DA11A47B283", "Myotis ciliolabrum", "Myotis ciliolabrum", 925, 31.2, 35.7, "forearm 31:2-35- 7 mm", ""),
    ("03A63743915FFFE3E4DFC5BF28E3A80A", "Pteronotus fuscus", "Pteronotus fuscus", 442, 56, 62, "forearm 56-62 mm", ""),
    ("03A63743915FFFE2E1DBC1E32DD4A4EE", "Pteronotus paraguanensis", "Pteronotus paraguanensis", 442, 52.6, 55.8, "forearm 52-6-55-8 mm", ""),
    ("03A637439150FFECE4EACCF02EB6ACD0", "Pteronotus pusillus", "Pteronotus pusillus", 441, 49.7, 52.9, "forearm 49-7-52-9 mm", ""),
    ("885887A2FFDD8A3AF896FB47F94CD195", "Rhinolophus nippon", "Rhinolophus nippon", 297, 49, 64, "forearm 49—64 mm", "Whole species; HMW gives 49-59 mm for the Japanese nominate subspecies and 58-64 mm for tragatus."),
    ("4C3D87E8FF636ADCFF819E1F1D6CB6BB", "Murina ryukyuana", "Murina ryukyuana", 913, 32.3, 38.1, "forearm 32-3-38- 1 mm", ""),
    ("03A687BCFF94FF97164EF411FCC7FB49", "Anoura peruana", "Anoura peruana", 521, 43, 49, "forearm 43-49 mm", ""),
    ("885887A2FFFE8A1BF8B4EFE6FC7FC876", "Rhinolophus perniger", "Rhinolophus perniger", 328, 68.5, 81, "forearm 68- 5-81 mm", "HMW notes its other measurements may include other taxa, but not the forearm."),
]


def midpoint(low: float, high: float) -> str:
    return number((low + high) / 2)


def main() -> None:
    pinned = {str(RAW_FILES[k]): v for k, v in RAW_SHA256.items()}
    pinned.update({str(PLAZI / f"{doc}.xml"): sha for doc, sha in PLAZI_SHA256.items()})
    check_raw(pinned)
    resolver = SizeResolver()
    rows = defaultdict(list)
    seen = defaultdict(int)

    def species_for(binomial: str, printed: str):
        species = resolver.by_bin.get(binomial)
        if not species:
            raise SystemExit(f"{binomial} is not an MDD v2.5 species")
        if printed == binomial:
            resolver.matched_exact += 1
            return species, "exact"
        resolver.matched_manual += 1
        return species, "manual"

    for (ref, raw, binomial, printed, locator, sex, stat, value, low, high, sd, n,
         area, verbatim, note) in ROWS:
        if raw not in RAW_FILES and raw not in PLAZI_SHA256:
            raise SystemExit(f"{ref}: raw file {raw} is not pinned")
        species, method = species_for(binomial, printed)
        seen[(ref, species["id"])] += 1
        if raw in PLAZI_SHA256:
            locator += f"; Plazi treatment {raw}"
        ranged = low is not None and high is not None
        rows[ref].append({
            "observation_id": f"{ref}-{species['id']}-{seen[(ref, species['id'])]}",
            "mdd_id": species["id"], "verbatim_taxon_name": printed, "taxon_match_method": method,
            "reference_id": ref, "locator": locator, "trait": "forearm_length", "basis": "measured",
            "statistic": stat, "value": number(value) if value is not None else midpoint(low, high),
            "value_min": number(low) if ranged else "", "value_max": number(high) if ranged else "",
            "range_type": "min_max" if ranged else "", "sd": number(sd) if sd is not None else "",
            "n": str(n) if n else "", "sex": sex, "area": area,
            "upstream_source": {"webala-2019": "guillen-servent-1996"}.get(ref, "")
            or ("malaga-2020" if "Málaga" in note else ""),
            "data_year": YEAR[ref], "verbatim_value": verbatim, "notes": note,
        })

    for doc, binomial, printed, page, low, high, verbatim, note in HMW:
        species, method = species_for(binomial, printed)
        single = low == high
        rows["hmw-2019"].append({
            "observation_id": f"hmw-2019-{species['id']}", "mdd_id": species["id"],
            "verbatim_taxon_name": printed, "taxon_match_method": method, "reference_id": "hmw-2019",
            "locator": f"p. {page}, Descriptive notes; Plazi treatment {doc}", "trait": "forearm_length",
            "basis": "measured", "statistic": "single" if single else "range_only",
            "value": number(low) if single else midpoint(low, high),
            "value_min": "" if single else number(low), "value_max": "" if single else number(high),
            "range_type": "" if single else "min_max", "n": "1" if single and "type specimen" in note else "",
            "sex": "pooled", "data_year": "2019", "verbatim_value": verbatim,
            "notes": ("Range compiled from the literature by HMW. " + note).strip(),
        })

    for ref, ref_rows in sorted(rows.items()):
        write_rows(ref, ref_rows)
        write_review(ref, [])
        print(f"{ref}: {len(ref_rows)} forearm rows for {len({r['mdd_id'] for r in ref_rows})} species")
    print(f"literature forearms: {sum(len(r) for r in rows.values())} rows for "
          f"{len({r['mdd_id'] for rs in rows.values() for r in rs})} species from {len(rows)} sources; "
          f"names: {resolver.matched_exact} as printed, {resolver.matched_manual} hand-checked")


if __name__ == "__main__":
    main()
