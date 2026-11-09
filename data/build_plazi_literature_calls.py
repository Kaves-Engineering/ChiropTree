"""Import call frequencies stated in species treatments held by Plazi.

For the bats that have a measured forearm but no measured peak frequency (the
call plot's gap list), every Plazi TreatmentBank treatment was searched for
call frequencies (November 2026). Three sources gave usable values:

- Handbook of the Mammals of the World 9 (2019), whose species accounts often
  summarise the call ("peak frequencies of 46-52 kHz"). Values are taken only
  as worded: text naming the peak, the frequency of most or maximum energy, or
  the frequency a harmonic peaks at -> peak_frequency; "CF component",
  "F component" or "call frequency of the F segment" of a leaf-nosed or
  horseshoe bat -> cf_frequency; "characteristic frequency" ->
  characteristic_frequency. A stated mean is a mean, a stated span is a range,
  a bare value is a species_summary and "c." makes it approximate. Plazi's OCR
  writes decimal points as hyphens, colons or bullets; verbatim_value keeps the
  OCR text and adds the reading in brackets.
- Colombo et al. (2018), the description of Pteronotus alitonus.
- Sedlock et al. (2020), Table 5, Kerivoula whiteheadi.

Excluded on reading: the treatment Plazi titles "Pharotis imogene" is the HMW
account of Ia io (its text names the Great Evening Bat), and FM-only
descriptions giving just start and end frequencies.

Raw files: data/raw/size/plazi/<docId>.xml, fetched from
https://tb.plazi.org/GgServer/xml/<docId> and pinned below.
Run: uv run data/build_plazi_literature_calls.py
"""
import hashlib
from pathlib import Path

from call_import_lib import TaxonResolver, report, write_review, write_rows

PLAZI = Path(__file__).parent / "raw" / "size" / "plazi"
PINS = {
    "03D587F2FFC24C0AF8DB3BECFAC2F083": "c89890a4e3244cf6ea7700995d21f4f4cd82ceabd9c2c04be0e99ee2bd6ddede",
    "03D587F2FFC74C0CFF1632ECFD40EE5E": "0427df3006496958ab60238c04fbbbbaeec144030b3af6c97c2de39c0e460138",
    "03A687BCFFBCFFBC13BEFABCF8D9F0D0": "ed14ae3cff8dc2d250e8be3efee2f7f45af21b1f17a0df935ce8e0e8262ac354",
    "E84887F9FFC7D6490AEBFD41146F3FEF": "2456b1b9a7ed9effef0f3d2eecdd4d76d2401e47ef8cf3c14918d62f6e836a59",
    "E84887F9FFD0D65E0F3AFCE919123DB7": "996095fd9e270ffc0ea7d77dc467b4dc5ca695f9d9177f0a0feb50c3152d24d2",
    "E84887F9FFD0D65F0F3EF41B14433004": "cecaf03fef49f0baf94b7036ad9be852c8bf3994a2fd893f7e60f2b1e04e638b",
    "E84887F9FFD2D65D0FC3F5CC11CC3142": "c463c39c534a05e4a4a73eccab62e75a04887f48caa6523c91d5b112fea9e51e",
    "4C3D87E8FF996A26FF58922B1FDDB6A4": "48dd9ebbdd840103ff59abb648a12d13a475f1bd08b507ee0718e5425459a5b0",
    "4C3D87E8FFCF6A70FF4C96A71A94B239": "8061cea6c7d8475c850ded038732838fa2d49b85acd1a49a3e99215fe2d2eb16",
    "194287C9FF9ABA36B195F3F5BBEAF444": "3bf18455139da9baef968ef32ed71255de793c74f2ace7df4b98b641cc30e872",
    "194287C9FFB8BA14B49BFC3DB408F955": "0edfa4b754ce64b95bcabf980d54c93923b6a60ca3e47a9634fcb757bb66b95a",
    "4C3D87E8FFD66A69FF7C92CD16BCBC0D": "7581ed3e246ab67058dbd499275d7e084c4167fce6d36f4ebfb22270f16d7c7b",
    "194287C9FF94BA38B49DF0E4BA2FFCF3": "87bf454d7f9bc7081b84b4dffe757a63a7b23c2acb2ee2ea4418624a0cf50a71",
    "4C3D87E8FFE96A56FF4C9B761710BCFC": "77aba39eb669452a66e1b71851cd238ad41ba7b8eba9e21061d2ff76876f03ed",
    "03A63743915FFFE3E4DFC5BF28E3A80A": "fea2d1f4aa8bff2693edef9ac4b289540e1d17a35bb60919e4428cfe6bc8f95f",
    "03A63743915FFFE2E1DBC1E32DD4A4EE": "fc0e526d0a9f909c83d7ca1a2bb54823835bd3913c64cdf719482576a62e9120",
    "03A637439150FFECE4EACCF02EB6ACD0": "f780a9ac4f7bac8045779d464e122b927e0e0cb712aca9fc9fab651f54e0abf3",
    "03A63743915FFFE3E4D9CAA02B9CAC20": "151972076854c9a5fc18e218384065d0edcf72724c33f2ca3bbf2d8ff9b0aae5",
    "03A637439150FFE3E1E6C1072BAAA348": "573be61fd52d07ed7c82e76e34f2c71ed51d582cda9bf0606ee9bff21de28583",
    "885887A2FFFC8A1AF8B1FD56F286D6A0": "203453a137f6de71b1c4cbe366360f36b7f831b64057d8e31835232cd3018153",
    "885887A2FFEC8A0AFF06F534F239DC09": "b03cf67ce6cf0706a32d8c41872cda5234ca71098812324c6251280c1628a736",
    "885887A2FFE78A00F895EE1CFAD4D2BF": "1d243005299a98f97b8baa55b94d870ea3cb096ccf2b564d217b58fed982f983",
    "885887A2FFD38A34F883F524F891DC55": "39920d719f13229ceab75be3a456cdac9e264fb5ff6caba3568cc2389da13ef5",
    "885887A2FFCC8A2DF84EFAC8FEA3DB68": "157b39412e88437ca2322a1b6723c62f07e8bae83df464bb12203ca351a29e39",
    "885887A2FFD28A37F8B2F7BCFB57DB41": "1c85238d8616c939cc555f40195f101bcd06af8a373452fc2e9d26c5d07f40c8",
    "03BD87A2C664A216FF55F87CFDE04CB7": "cf55a75e61f2ab2c660136b6b682c6af68acc87333ce96a8609e9d26fafe7354",
    "03BD87A2C663A211F878FD37F2574AFE": "88a2b5c8c4025273de335ef2296c884ee825556af75e1b8c05c1f9ef1a225f95",
    "03BD87A2C664A216FF55EFC7F2B844F7": "6cb822d7b49c85ed4cfe4fcd4e831af1d8210de9f31460ca713347d59fb9b276",
    "03BD87A2C66CA21EFF54F6C8FB1F53FA": "544647b4627a8b058ce5bfdfb9d5c9fe7c9f8876707d5ff6e351f2d018b63a61",
    "03BD87A2C66BA21AF877F349FDE14058": "3650ea47a03142079840689601349390375913b84d1d548e457a05bcfa686529",
    "03BD87A2C668A21AFF48F5F3F8EB514E": "b6369adef78966f98e2e28580f5d524344ecb8444d87be5b033c30cbc036487d",
    "03BD87A2C668A21AF89AF71DF3CE5141": "8305948d7e37c0ca47f76157b8793e4807d2846663fa10e5ea3ef7fc923c8a16",
    "03BD87A2C675A207F87BF8D5F50853B9": "a3f262ad3578dbd73489947a4d5929a61b6058b389593adcb34b143527d4b051",
    "4C3D87E8FFB46A0BFF7997F21FD8B734": "485a6fd0813917707afbf1b56ccd578ac17f09d11f32638e64ab7fe204c5a10e",
    "4C3D87E8FF856A3BFA7C9D3C1B20B05C": "59a7ab3aa652a094901bad2888a940bebf80e0774cda743463c803b113f5d8c0",
    "4C3D87E8FFD56A6AFF4C9B56145DB29C": "cbc498f186969919323a875b1d199b81dbb59b3a781dcbbadd52ff80ffc9a736",
    "4C3D87E8FF5C6AECFA909EB21C43B3F4": "a9545688ebd067e18dc8162e1b4cec2c8dbb257c402ae0f38ee4d0ddb7332b10",
    "46341E41E13EE51BFC495ED1FE4FC1FD": "a4fca9fbba6c9b0000eba7b7c184acc76abe42c23a4e7da2a0c12c920e483bd1",
    "5316885DF470FFEBFF0CD46CFAC7F84E": "cdcfc5bc6e3ffd2bc6465a5cb412eca4aa4994e841fc2565238f59dea748a27c",
}
METHODS = {"hmw-2019": "hmw-2019-compiled", "colombo-2018-pteronotus": "colombo-2018-pteronotus-field",
           "sedlock-2020-kerivoula": "sedlock-2020-kerivoula-field"}
UNITS = {"duration": "ms"}

PK, CF, CH, MX, MN, ST, EN, DU, KN = ("peak_frequency", "cf_frequency", "characteristic_frequency",
                                       "max_frequency", "min_frequency", "start_frequency",
                                       "end_frequency", "duration", "knee_frequency")
H = "hmw-2019"


def r(ref, doc, page, species, obs, parameter, statistic, value=None, low=None, high=None, *,
      verbatim, sd=None, harmonic="", country="", locality="", condition="unspecified",
      n="", flag="ok", note=""):
    return dict(ref=ref, doc=doc, page=page, species=species, obs=obs, parameter=parameter,
                statistic=statistic, value=value, low=low, high=high, sd=sd, harmonic=harmonic,
                country=country, locality=locality, condition=condition, n=n, flag=flag,
                verbatim=verbatim, note=note)


ROWS = [
    # --- HMW 2019, peak frequency -------------------------------------------
    r(H, "03D587F2FFC24C0AF8DB3BECFAC2F083", 362, "Coleura seychellensis", "a", PK, "range", None, 39.2, 41.1, harmonic="1", country="Seychelles",
      verbatim="first harmonic peaking at frequencies of 39-2-41 • 1 kHz [39.2–41.1]"),
    r(H, "03A687BCFFBCFFBC13BEFABCF8D9F0D0", 497, "Lonchorhina aurita", "ca", PK, "species_summary", 45,
      verbatim="Peak frequency of CF components is 45 kHz in Central America", locality="Central America"),
    r(H, "03A687BCFFBCFFBC13BEFABCF8D9F0D0", 497, "Lonchorhina aurita", "br", PK, "approximate", 50, country="Brazil",
      verbatim="c.50 kHz in north-eastern Brazil [50]", locality="north-eastern Brazil"),
    r(H, "E84887F9FFC7D6490AEBFD41146F3FEF", 708, "Miniopterus majori", "a", PK, "range", None, 46.1, 52, country="Madagascar",
      verbatim="peak frequencies of 46-1-52 kHz [46.1–52]"),
    r(H, "E84887F9FFC7D6490AEBFD41146F3FEF", 708, "Miniopterus majori", "a", MX, "range", None, 64, 102, country="Madagascar",
      verbatim="maximum frequencies of 64-102 kHz"),
    r(H, "E84887F9FFC7D6490AEBFD41146F3FEF", 708, "Miniopterus majori", "a", MN, "range", None, 43, 46, country="Madagascar",
      verbatim="minimum frequencies of 43-46 kHz"),
    r(H, "E84887F9FFC7D6490AEBFD41146F3FEF", 708, "Miniopterus majori", "a", DU, "range", None, 2.8, 4.5, country="Madagascar",
      verbatim="durations of 2-8-4-5 milliseconds [2.8–4.5]"),
    r(H, "E84887F9FFD0D65E0F3AFCE919123DB7", 697, "Miniopterus macrocneme", "a", PK, "range", None, 42, 45, country="New Caledonia",
      verbatim="peak frequencies of 42—45 kHz in New Caledonia"),
    r(H, "E84887F9FFD0D65F0F3EF41B14433004", 697, "Miniopterus robustior", "a", PK, "range", None, 42, 45, country="New Caledonia",
      verbatim="peak frequencies of 42-45 kHz"),
    r(H, "E84887F9FFD2D65D0FC3F5CC11CC3142", 695, "Miniopterus tristis", "a", MN, "mean", 34.6,
      verbatim="mean minimum frequency is 34-6 kHz [34.6]"),
    r(H, "4C3D87E8FF996A26FF58922B1FDDB6A4", 856, "Bauerus dubiaquercus", "a", PK, "mean", 36.3, harmonic="1",
      verbatim="peak frequency 36-3 kHz [36.3]", note="The account states the fundamental is the peak harmonic."),
    r(H, "4C3D87E8FF996A26FF58922B1FDDB6A4", 856, "Bauerus dubiaquercus", "a", MX, "mean", 61.6, harmonic="1", verbatim="maximum frequency 61-6 kHz [61.6]"),
    r(H, "4C3D87E8FF996A26FF58922B1FDDB6A4", 856, "Bauerus dubiaquercus", "a", MN, "mean", 27.4, harmonic="1", verbatim="minimum frequency 27-4 kHz [27.4]"),
    r(H, "4C3D87E8FF996A26FF58922B1FDDB6A4", 856, "Bauerus dubiaquercus", "a", DU, "mean", 3.2, verbatim="call duration 3-2 milliseconds [3.2]"),
    r(H, "4C3D87E8FFCF6A70FF4C96A71A94B239", 810, "Hypsugo arabicus", "a", PK, "range", None, 31.9, 36.5, country="Oman",
      verbatim="peak frequencies of 31:9-36-5 kHz [31.9–36.5]"),
    r(H, "4C3D87E8FFCF6A70FF4C96A71A94B239", 810, "Hypsugo arabicus", "a", ST, "range", None, 36.1, 48.5, country="Oman",
      verbatim="start frequencies of 36-1-48-5 kHz [36.1–48.5]"),
    r(H, "4C3D87E8FFCF6A70FF4C96A71A94B239", 810, "Hypsugo arabicus", "a", EN, "range", None, 30, 34.4, country="Oman",
      verbatim="end frequencies of 30-34-4 kHz [30–34.4]"),
    r(H, "4C3D87E8FFCF6A70FF4C96A71A94B239", 810, "Hypsugo arabicus", "a", DU, "range", None, 6.6, 8.8, country="Oman",
      verbatim="durations of 6-6—8-8 milliseconds [6.6–8.8]"),
    r(H, "194287C9FF9ABA36B195F3F5BBEAF444", 657, "Mops sarasinorum", "a", PK, "range", None, 20, 24,
      verbatim="frequency of maximum energy is 20-24 kHz"),
    r(H, "194287C9FF9ABA36B195F3F5BBEAF444", 657, "Mops sarasinorum", "a", DU, "range", None, 4, 16,
      verbatim="Duration is 4-16 milliseconds"),
    r(H, "194287C9FFB8BA14B49BFC3DB408F955", 623, "Mormopterus minutus", "a", PK, "mean", 43, country="Cuba",
      verbatim="average peak frequency of 43 kHz"),
    r(H, "4C3D87E8FFD66A69FF7C92CD16BCBC0D", 803, "Nyctophilus gouldi", "a", PK, "mean", 51.8, 50, 53, country="Australia",
      verbatim="Peak frequencies are 50-53 kHz (mean 51-8 kHz) [51.8]"),
    r(H, "194287C9FF94BA38B49DF0E4BA2FFCF3", 659, "Otomops wroughtoni", "a", PK, "species_summary", 15.3, condition="hand_release",
      verbatim="peak frequency of 15-3 kHz [15.3]"),
    r(H, "194287C9FF94BA38B49DF0E4BA2FFCF3", 659, "Otomops wroughtoni", "a", ST, "species_summary", 18.5, condition="hand_release",
      verbatim="start frequency is 18-5 kHz [18.5]"),
    r(H, "194287C9FF94BA38B49DF0E4BA2FFCF3", 659, "Otomops wroughtoni", "a", EN, "species_summary", 12.4, condition="hand_release",
      verbatim="end frequency is 12-4 kHz [12.4]"),
    r(H, "194287C9FF94BA38B49DF0E4BA2FFCF3", 659, "Otomops wroughtoni", "a", DU, "range", None, 48, 60, condition="hand_release",
      verbatim="durations of 48-60 milliseconds"),
    r(H, "4C3D87E8FFE96A56FF4C9B761710BCFC", 776, "Pipistrellus inexspectatus", "a", PK, "single", 54.7, country="Cameroon", locality="Maroua",
      verbatim="peak frequency of 54-7 kHz [54.7]", note="One call."),
    r(H, "4C3D87E8FFE96A56FF4C9B761710BCFC", 776, "Pipistrellus inexspectatus", "a", MN, "single", 47.7, country="Cameroon", locality="Maroua",
      verbatim="minimum frequency of 47-7 kHz [47.7]", note="One call."),
    r(H, "4C3D87E8FFE96A56FF4C9B761710BCFC", 776, "Pipistrellus inexspectatus", "a", KN, "single", 54.7, country="Cameroon", locality="Maroua",
      verbatim="knee frequency of 54-7 kHz [54.7]", note="One call."),
    r(H, "4C3D87E8FFE96A56FF4C9B761710BCFC", 776, "Pipistrellus inexspectatus", "a", CH, "single", 47.7, country="Cameroon", locality="Maroua",
      verbatim="characteristic frequency of 47-7 kHz [47.7]", note="One call."),
    r(H, "4C3D87E8FFE96A56FF4C9B761710BCFC", 776, "Pipistrellus inexspectatus", "a", DU, "single", 0.46, country="Cameroon", locality="Maroua",
      verbatim="duration of 0-46 milliseconds [0.46]", note="One call.", flag="suspect"),
    r(H, "03A63743915FFFE3E4DFC5BF28E3A80A", 442, "Pteronotus fuscus", "ve", PK, "approximate", 62, country="Venezuela",
      verbatim="most energy at a frequency of c.62 kHz in Venezuelan populations [62]"),
    r(H, "03A63743915FFFE3E4DFC5BF28E3A80A", 442, "Pteronotus fuscus", "tt", PK, "approximate", 58.9, country="Trinidad and Tobago",
      verbatim="Trinidadian individuals is lower at c.58-9 kHz [58.9]"),
    r(H, "03A63743915FFFE2E1DBC1E32DD4A4EE", 442, "Pteronotus paraguanensis", "a", PK, "approximate", 68, country="Venezuela",
      verbatim="most energy at frequency of c.68 kHz"),
    r(H, "03A637439150FFECE4EACCF02EB6ACD0", 441, "Pteronotus pusillus", "a", PK, "approximate", 67.5, country="Haiti",
      verbatim="most energy at c.67-5 kHz [67.5]"),
    r(H, "885887A2FFFC8A1AF8B1FD56F286D6A0", 330, "Rhinolophus beddomei", "a", PK, "range", None, 38.5, 38.7, country="India", locality="Western Ghats",
      verbatim="peak F recorded at 38-5—38-7 kHz [38.5–38.7]"),
    r(H, "885887A2FFFC8A1AF8B1FD56F286D6A0", 330, "Rhinolophus beddomei", "b", PK, "mean", 42.8, 41.7, 43.3, country="India", locality="Western Ghats",
      verbatim="peak frequencies of 41-7-43-3 kHz (mean 42-8 kHz) [42.8]", note="A second study; HMW rejects a third (Sri Lanka, 41-62.5 kHz) as an error."),
    r(H, "885887A2FFEC8A0AFF06F534F239DC09", 314, "Rhinolophus cognatus", "a", PK, "mean", 89.9, 85.2, 92.1, country="India", locality="Andaman Islands",
      verbatim="peak F of 85-2-92-1 kHz (mean 89-9 kHz) [89.9]"),
    r(H, "885887A2FFE78A00F895EE1CFAD4D2BF", 319, "Rhinolophus inops", "a", PK, "mean", 55.1, country="Philippines",
      verbatim="mean peak frequency of 55-1 kHz [55.1]"),
    r(H, "885887A2FFD38A34F883F524F891DC55", 307, "Rhinolophus virgo", "a", PK, "mean", 85.6, 83, 88, country="Philippines", locality="Laguna Province, Luzon",
      verbatim="peak F recorded at 83-88 kHz (averaging 85-6 kHz) [85.6]"),
    r(H, "4C3D87E8FFB46A0BFF7997F21FD8B734", 837, "Scotomanes ornatus", "vn", PK, "range", None, 29.7, 35.9, country="Vietnam",
      verbatim="peak frequencies of 29-7-35-9 kHz [29.7–35.9]"),
    r(H, "4C3D87E8FFB46A0BFF7997F21FD8B734", 837, "Scotomanes ornatus", "vn", ST, "range", None, 43, 62, country="Vietnam", verbatim="start frequencies of 43-62 kHz"),
    r(H, "4C3D87E8FFB46A0BFF7997F21FD8B734", 837, "Scotomanes ornatus", "vn", EN, "range", None, 18.6, 23.1, country="Vietnam",
      verbatim="end frequencies of 18-6-23-1 kHz [18.6–23.1]"),
    r(H, "4C3D87E8FFB46A0BFF7997F21FD8B734", 837, "Scotomanes ornatus", "vn", DU, "range", None, 2.2, 4.4, country="Vietnam",
      verbatim="durations of 2:2—4-4 milliseconds [2.2–4.4]"),
    r(H, "4C3D87E8FF856A3BFA7C9D3C1B20B05C", 885, "Scotophilus heathii", "a", PK, "mean", 41.2, 37.4, 59.6, country="India", locality="Western Ghats",
      verbatim="average peak frequency was 41-2 kHz (37-4-59-6 kHz) [41.2]"),
    r(H, "4C3D87E8FF856A3BFA7C9D3C1B20B05C", 885, "Scotophilus heathii", "a", ST, "mean", 56.7, 43.2, 83.8, country="India", locality="Western Ghats",
      verbatim="average start frequency was 56-7 kHz (43-2-83-8 kHz) [56.7]"),
    r(H, "4C3D87E8FF856A3BFA7C9D3C1B20B05C", 885, "Scotophilus heathii", "a", EN, "mean", 37.7, 33.8, 43, country="India", locality="Western Ghats",
      verbatim="average end frequency was 37-7 kHz (33-8-43 kHz) [37.7]"),
    r(H, "4C3D87E8FF856A3BFA7C9D3C1B20B05C", 885, "Scotophilus heathii", "a", DU, "mean", 2.7, 2.2, 3.5, country="India", locality="Western Ghats",
      verbatim="average duration was 2-7 milliseconds (2-2-3-5 milliseconds) [2.7]"),
    r(H, "4C3D87E8FF5C6AECFA909EB21C43B3F4", 929, "Myotis occultus", "a", PK, "mean", 46, verbatim="peak frequency of 46 kHz"),
    r(H, "4C3D87E8FF5C6AECFA909EB21C43B3F4", 929, "Myotis occultus", "a", CH, "mean", 34.9, verbatim="characteristic frequency of 34-9 kHz [34.9]"),
    r(H, "4C3D87E8FF5C6AECFA909EB21C43B3F4", 929, "Myotis occultus", "a", MX, "mean", 81.7, verbatim="maximum frequency of 81-7 kHz [81.7]"),
    r(H, "4C3D87E8FF5C6AECFA909EB21C43B3F4", 929, "Myotis occultus", "a", MN, "mean", 33.7, verbatim="minimum frequency of 33-7 kHz [33.7]"),
    r(H, "4C3D87E8FF5C6AECFA909EB21C43B3F4", 929, "Myotis occultus", "a", DU, "mean", 3, verbatim="duration of 3 milliseconds"),
    # --- HMW 2019, CF and characteristic frequency (not peak) -----------------
    r(H, "03A63743915FFFE3E4D9CAA02B9CAC20", 442, "Pteronotus mesoamericanus", "yu", CF, "species_summary", 63.5, harmonic="2", country="Mexico",
      locality="Yucatan Peninsula", verbatim="CF component of 63-5 kHz [63.5]", note="The account states most energy is in the second harmonic."),
    r(H, "03A63743915FFFE3E4D9CAA02B9CAC20", 442, "Pteronotus mesoamericanus", "cr", CF, "mean", 60.5, harmonic="2", country="Costa Rica",
      verbatim="mean CF of individuals from Costa Rica 1s 60-5 kHz [60.5]", note="The account states most energy is in the second harmonic."),
    r(H, "03A637439150FFE3E1E6C1072BAAA348", 441, "Pteronotus mexicanus", "a", CF, "approximate", 64, harmonic="2", country="Mexico",
      verbatim="CF component of second harmonic is c.64 kHz [64]"),
    r(H, "885887A2FFCC8A2DF84EFAC8FEA3DB68", 282, "Rhinolophus guineensis", "a", CF, "species_summary", 85, country="Guinea",
      verbatim="F component of 85 kHz in Guinea"),
    r(H, "885887A2FFD28A37F8B2F7BCFB57DB41", 308, "Rhinolophus robinsoni", "a", CF, "range", None, 64, 68, verbatim="F of 64-68 kHz"),
    r(H, "03BD87A2C664A216FF55F87CFDE04CB7", 245, "Hipposideros jonesi", "a", CF, "range", None, 46, 48, verbatim="F component at 46-48 kHz"),
    r(H, "03BD87A2C663A211F878FD37F2574AFE", 248, "Hipposideros lamottei", "a", CF, "species_summary", 119, verbatim="F component at 119 kHz"),
    r(H, "03BD87A2C664A216FF55EFC7F2B844F7", 245, "Hipposideros marisae", "a", CF, "species_summary", 146, verbatim="F component at 146 kHz"),
    r(H, "03BD87A2C66CA21EFF54F6C8FB1F53FA", 253, "Hipposideros doriae", "a", CF, "range", None, 195, 200, verbatim="Call frequency of the F segment is 195-200 kHz"),
    r(H, "03BD87A2C66BA21AF877F349FDE14058", 256, "Hipposideros obscurus", "a", CF, "range", None, 138, 145, country="Philippines",
      verbatim="Call frequency is 138-145 kHz", flag="definition_unstated", note="'Call frequency' unqualified; read as the CF component, as for the genus elsewhere in HMW."),
    r(H, "03BD87A2C668A21AFF48F5F3F8EB514E", 257, "Hipposideros papua", "a", CF, "approximate", 123, country="Indonesia",
      verbatim="Call frequency of the F segment is c.123 kHz"),
    r(H, "03BD87A2C668A21AF89AF71DF3CE5141", 257, "Hipposideros pygmaeus", "a", CF, "approximate", 95.5, country="Philippines",
      verbatim="Call frequency of the F segment is c.95-5 kHz [95.5]"),
    r(H, "03BD87A2C675A207F87BF8D5F50853B9", 230, "Doryrhina cyclops", "a", CF, "approximate", 60, verbatim="F component at c.60 kHz"),
    r(H, "03D587F2FFC74C0CFF1632ECFD40EE5E", 357, "Saccolaimus mixtus", "a", CH, "species_summary", 21, verbatim="characteristic frequency of 21 kHz"),
    r(H, "4C3D87E8FFD56A6AFF4C9B56145DB29C", 804, "Nyctophilus microtis", "ng", CH, "approximate", 40, country="Papua New Guinea",
      verbatim="characteristic frequency of c.40 kHz on New Guinea", locality="New Guinea"),
    # --- primary descriptions -------------------------------------------------
    r("colombo-2018-pteronotus", "46341E41E13EE51BFC495ED1FE4FC1FD", 630, "Pteronotus alitonus", "a", PK, "mean", 59.2, 58.4, 61.5, harmonic="2",
      country="Brazil", locality="central Amazon", verbatim="average FME of 59.2 kHz (58.4– 61.5 kHz)",
      note="FME, frequency of maximum energy; the paper states the second harmonic, when present, is the most intense."),
    r("colombo-2018-pteronotus", "46341E41E13EE51BFC495ED1FE4FC1FD", 630, "Pteronotus alitonus", "a", DU, "mean", 24.8, 7.0, 40.0,
      country="Brazil", locality="central Amazon", verbatim="signal duration of 24.8 ms (7.0–40.0 ms)"),
    r("sedlock-2020-kerivoula", "5316885DF470FFEBFF0CD46CFAC7F84E", 473, "Kerivoula whiteheadi", "a", PK, "mean", 138.09, 125.06, 144.74, sd=5.69,
      country="Philippines", verbatim="138.09 ± 5.69 144.74-125.06", note="Table 5 prints n = 16."),
    r("sedlock-2020-kerivoula", "5316885DF470FFEBFF0CD46CFAC7F84E", 473, "Kerivoula whiteheadi", "a", DU, "mean", 1.77, 0.84, 2.73, sd=0.56,
      country="Philippines", verbatim="1.77 ± 0.56 2.73-0.84", note="Table 5 prints n = 16."),
    r("sedlock-2020-kerivoula", "5316885DF470FFEBFF0CD46CFAC7F84E", 473, "Kerivoula whiteheadi", "a", ST, "mean", 194.38, 160.4, 223.06, sd=18.75,
      country="Philippines", verbatim="194.38 ± 18.75 223.06-160.4", note="Table 5 prints n = 16."),
    r("sedlock-2020-kerivoula", "5316885DF470FFEBFF0CD46CFAC7F84E", 473, "Kerivoula whiteheadi", "a", EN, "mean", 75.77, 48.24, 107.51, sd=15.55,
      country="Philippines", verbatim="75.77 ± 15.55 107.51-48.24", note="Table 5 prints n = 16."),
]


def num(x) -> str:
    return "" if x is None else f"{x:g}"


def main() -> None:
    for doc, expected in PINS.items():
        got = hashlib.sha256((PLAZI / f"{doc}.xml").read_bytes()).hexdigest()
        if got != expected:
            raise SystemExit(f"{doc}.xml: sha256 {got} does not match the pinned {expected}")
    resolver = TaxonResolver()
    out, seen = {}, {}
    for row in ROWS:
        if row["doc"] not in PINS:
            raise SystemExit(f"{row['doc']} is not pinned")
        species, method = resolver.resolve(row["species"])
        if species is None:
            continue
        ref = row["ref"]
        seen.setdefault(ref, set()).add(species["id"])
        label = "Table 5" if ref == "sedlock-2020-kerivoula" else "species account"
        out.setdefault(ref, []).append({
            "observation_id": f"{ref}-{species['id']}-{row['obs']}", "mdd_id": species["id"],
            "verbatim_taxon_name": row["species"], "taxon_match_method": method, "reference_id": ref,
            "locator": f"p. {row['page']}, {label}; Plazi treatment {row['doc']}", "method_id": METHODS[ref],
            "call_phase": "unspecified", "recording_condition": row["condition"],
            "country": row["country"], "locality": row["locality"], "n_individuals": row["n"],
            "parameter": row["parameter"], "statistic": row["statistic"], "value": num(row["value"]),
            "value_min": num(row["low"]), "value_max": num(row["high"]),
            "unit": UNITS.get(row["parameter"], "kHz"),
            "dispersion_type": "sd" if row["sd"] is not None else "", "dispersion_value": num(row["sd"]),
            "harmonic": row["harmonic"], "verbatim_value": row["verbatim"], "quality_flag": row["flag"],
            "notes": row["note"],
        })
    for ref, rows in out.items():
        write_rows(ref, rows)
        write_review(ref, resolver.unresolved)
        report(ref, len(rows), len(seen[ref]), resolver)


if __name__ == "__main__":
    main()
