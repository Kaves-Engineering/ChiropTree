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
import re
from pathlib import Path

from call_import_lib import TaxonResolver, report, write_review, write_rows

PLAZI = Path(__file__).parent / "raw" / "size" / "plazi"
# Treatments found later by data/calls/search_call_gaps.py are cached here.
PLAZI_CALLS = Path(__file__).parent / "raw" / "calls" / "plazi"


def xml_path(doc: str) -> Path:
    first = PLAZI / f"{doc}.xml"
    return first if first.exists() else PLAZI_CALLS / f"{doc}.xml"


def xml_page(doc: str) -> int:
    """The printed page a treatment starts on, from its pageNumber attribute."""
    import re as _re
    head = xml_path(doc).read_bytes()[:4000].decode("utf-8", "replace")
    return int(_re.search(r'pageNumber="(\d+)"', head).group(1))
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
    # call-gap search, November 2026 (data/raw/calls/plazi/)
    "0383245F2225977B8BD5F631FD78FE56": "9914e51192e63a1130c998245a9ecff09d4cecf1340061d8a18265740a3e0ee5",
    "0383245F222797788EC5F396F852FB4D": "74b0d8fe6d447708afc855979f1d0fc7dcc70104ebc87429655483296f258c9a",
    "03A687BCFFBBFFBA138DF33DFB38FF43": "eb33cf3424ee8d7c5308c006fea12b596727d85a3b71ce8811ddc146adf9274c",
    "03B0BC062412FFD4FF31EC79FBA6F24C": "8c492275370df0eae744b465d670262e853ac1a38e4622373d54fde82309c031",
    "03BD87A2C660A212FF52F3F7F35547D7": "c44cfa7cb2a9b662a112acec7add94cb519e2512a8dde1946f665ad3535deef6",
    "03BD87A2C666A214FF55F782F74F4BFC": "20dd5bcd78f7111ae01a0e33f745b999a08c8229d2327cfb34bb451ece8b61d5",
    "03BD87A2C668A21AFF50FC16FEFE4ABD": "5c02f76d60282037209c70212d52495aeffda6d36b81e9d58f72c92b9e8d38cb",
    "03BD87A2C669A21BF872FECBF5B74BD3": "d46127cd56b7138639e3883d119670a577ee4d32859bc2d87391c96750aec678",
    "03BD87A2C66AA218F8ACF806F537533A": "ec62e9bb93394b93aa7b5cf23a4ec9b9682af3880562704230dbd1fd433fb7b2",
    "03BD87A2C66AA218FF5DEF31F3984475": "0e8e05fa98cee757070b0baedb1b24bca600fdfe1814776a4893e2cf3978d2fa",
    "03BD87A2C671A203FF3CFDBBFEF54D68": "e95149361db58454a942d27d2ab89ad7113f8b10eddbd98101a8c2e93beee1ae",
    "03BD87A2C672A200FF5AF605FE6052B8": "75cc504156526f84ae013ef23833f4b4c3b8393ea28a1f48f8718bbeb531bd0f",
    "03BD87A2C67BA20AF882F09AFA924472": "1ef99e3ba2622d3c35a151f9e9b296eaa4d076578467b78e3e002aad36698d01",
    "03BD87A2C67CA20EF89EFC3DF79F4EBC": "847701f1e0cc3d26c344daee025f65cb74bc57c822fdd875b950ae243d7dd4f3",
    "03BD87A2C67CA20EFF4BF595F4A8407C": "22a0cf211232dc06827c7107fc74fbde57ee672a88ba5cb1f1cb763288efef14",
    "03BD87A2C67DA20FF87DFECAF79849EC": "dab4e1b022535c86c804fa099c48a3882b0b2738be7b622d3b7fd8503219ccf9",
    "03BD87A2C67DA20FFF31F64EFB1C5151": "abd0826310b5d3209769e1ff02d6529d4ccb953d3986ed0ffe13e726fcc23347",
    "03D587F2FFC14C0AFF113AAFF5B6F633": "a25bd42ee43f23552cb08148c8a36f7ab6386f5cb9149ebf4fc5c42a4f18ada8",
    "03D587F2FFC34C08FF0337D6FEFCF45F": "ca94772533f9038e2297c2b7e089cb3b4ba5e409af5f58714955b1c8ba67aed2",
    "03D587F2FFCA4C02F82F3255F947FAAB": "c36e8bcfc84906df86d2e4e7cb229108972ea1b34ef06558b92c8cdf42a79b10",
    "194287C9FF88BA24B481F57BB17EF4AE": "c6ec8d971565dca2d5dde8fa866aae091d7300972675ef8c0c1067d006938afc",
    "194287C9FF88BA24B484FCC5B504F726": "c355a02a77db292098a0f05edfbed9d34a39fc211f4eb65440371079bbbc6035",
    "194287C9FFA2BA0EB498FA6BBB40F839": "49c033aa99ed865c32fe046b196e503a6a1f7fd9c86afa55f3d217eab7dee56a",
    "194287C9FFA3BA0FB1A5F213BBB4F373": "0f5e5c787b74db495b56af25cc693ce990e2219257da650ad8f018b5b001b5cd",
    "194287C9FFA8BA04B49CFA5BBABDF6D8": "0ef541d35c7de568120aadcce7763a375ae4f6a5a0a4592c5be6faecb761f859",
    "194287C9FFB4BA18B49BFDA6BB02F922": "34bdfe7379eb30871770bb2e8c9d057c0f26f59593a9f412f3e70e5c3a9d3eaf",
    "194287C9FFBABA17B19CF05FB007FC93": "847bc538020f4943b62564881e1cb8d5b506d7f82847e25a05dbd8c82a42d246",
    "290787FFFFA71877FA149D33EF413C1D": "4ba5cbcdde61272166361a50b64327491796fe4182dedabebdb8f43773cf7fd2",
    "4C3D87E8FF326A8DFF869A0718EBB150": "23dab709156209aa2beafd050d3d9dfe65efc938b4a9705f34684e1431738980",
    "4C3D87E8FF376A88FF5B95201C39B20B": "ab303d88a58827ed56ed381884b7d80888a1fbdfe8058b1672d5166d31245060",
    "4C3D87E8FF386A87FA8495181BBFB152": "96705030cf56c7a7683ff995c725a60a7eede96bc7e930a3d1cedf802f02fda6",
    "4C3D87E8FF3C6A83FF72975E17F9BAE5": "95610f9a7c5239d1f59bdcb95aa5f580b7ec7ec6007157cb0283598530932990",
    "4C3D87E8FF436AFCFA52936D161AB625": "8de9d1a674f8f53c6f915f2c98de8bd18132581b1193894e3992bfd6563135a4",
    "4C3D87E8FF536AEDFA4B91961C1EB82A": "19f805c98ef3503b28ddb6699470bb465f8e9512d82dc76b219e802103cc60b7",
    "4C3D87E8FF566AE9FF8791F21903B086": "4f5deb5add7b4bc14eec5a78974ca2096085905c725b4fb5e7d1743cfadceeca",
    "4C3D87E8FF616ADEFF78974D1DB6B31B": "49b16682c6d541e8bc919b13b018812462df8082a31b198947bd68f90c3b5a59",
    "4C3D87E8FF616ADEFF859E2F1636BF37": "ebc49bca0d700ad30bbbdcf6e67e880d41b2a09e1750ef2caa047693acea7fee",
    "4C3D87E8FF656ADBFA7D9E591DC0B97D": "74a47c9cbf88ba610d49a208912ab50f2f52bf3cb25e86064a7e8be5032b660f",
    "4C3D87E8FF666ADAFA489FA61CE4BFF2": "ae9f8d84614c704e3a6d8583dac2131a90203bf1b0aa46a4313b488f92303249",
    "4C3D87E8FF676AD8FF879F51198FBF79": "74ce2123ca104aca880ec0ce520d51741cdc960f6190e98df7abaccfd9679cd5",
    "4C3D87E8FF6C6AD3FF4091451447BAA0": "2c36c0be17f43a8a999fa3cbdd2d9d1e3a62a3426d8864709590dbe5533595f0",
    "4C3D87E8FF6E6AD2FA479DE01D9ABED7": "6c7ba034e9b4bbdd2706cf1fecd864182d14f2161c6698b6d52fef4f5f41cd71",
    "4C3D87E8FF716ACEFA55945E17E6B279": "9cfe3c3e6d96087b7b6a4b6855c90abed4e7fae8e1e8a70ac82e601bcbe65f9d",
    "4C3D87E8FF716ACEFF5097451C54B350": "e4e4bd3a9dbc3f37d840050689f28b8c9bcaaee123fbe8349ac441550e334519",
    "4C3D87E8FF716ACFFA519FCD1DFEBFB9": "10412e6d266a8412c4e919614863ffa85e5b8e0852b55b2b3e67368b1c716041",
    "4C3D87E8FF8A6A35FF7E95A01FABB71B": "65d4a1e6f955fdbce27fbc33d826a3d1b131fa65c1af3c010135eba240b4e273",
    "4C3D87E8FF8D6A33FA579EC91D96BEE5": "8c8a91988ad6c61130c8b0ba7b0f95cc6ad13520f461108cc21d3733354e556a",
    "4C3D87E8FF976A28FF4C935C18A1BAE2": "a95d5b945fca83fd368131f7b45a9425de472b986014933f7a9c44a9140172de",
    "4C3D87E8FFAD6A12FF449168192DB80B": "479d8e6a28bf31636be20ec33fa0683b394e0ca3a053957d80ec522ea75792c4",
    "4C3D87E8FFB96A06FF499FC51787BCF0": "475c996408343b9854a0e320a31909ddd7aa65418eeda7643f3f0590e897b828",
    "4C3D87E8FFBB6A04FF489C8B1458BCA0": "9df18138df2d6a4faa5076b4d0736190fcbc228ff37e86479270cd84bb0bb50a",
    "4C3D87E8FFBE6A01FF87936417F4BE28": "506b16572286b3613d07bdf9a90cd1408fc5169288ba3786df698980f7a6c6f0",
    "4C3D87E8FFC26A7DFF8A9FD918CEBFD4": "500302a0960df8930733639a7f8a9a1c10f8d2584d711015e8310748764ab1c8",
    "4C3D87E8FFC86A77FA80932416A8B77E": "6e2679a7b614acfb968338be7370259b6377c6eaebfe82f0a50bec3c7443dc05",
    "4C3D87E8FFD06A68FA8593731B32BDF0": "61518c3726ebfc50884e8abe8758db37212cdee47f2fb39bd3725f7a0923e9bb",
    "4C3D87E8FFD76A69FA5590CB1C38BF7D": "2c2b78a69a4f660fff9adec5b2c90e4de5ce0ea49ced9cb52595a25ff1afa8f9",
    "4C3D87E8FFDC6A63FF7E9247180DBA6F": "d408e6ce9b3482e6642d2e206bd434935bec50f9a6aa0dabb4a9568bf81ec3b0",
    "4C3D87E8FFE36A5CFF4B951F1D2AB15B": "23ba1cdb3a3a2f8f56464ccd08f5bda0768a712e43e742b8865f72f867dfa564",
    "4C3D87E8FFE86A57FA8A9061193AB7A3": "f6a5ddcd8058cdb0868d1900c155a49e4feebe5bccd3fa3b8aa0425eda835110",
    "4C3D87E8FFE86A57FF869F081428BEDD": "df7e29414f8cca2d21bdf3369a11785138cdb58b5d761fa7c58493d99181f593",
    "4C3D87E8FFED6A52FF4895151B5EB694": "73284acdec0cbeddacf5c5cc326c84347ff7228a6d546375c30836e114955858",
    "4C3D87E8FFEE6A52FA97928D1A44B831": "2e3271586b9879e6ac7b7134536787fcdbb2e698b7bcac1309748712794a9a37",
    "4C3D87E8FFF56A4AFA58977D1959B266": "82795a02c2599f47207579773a52ef6f438b532f0759227b6627eaf375bb8e33",
    "4C3D87E8FFF56A4BFA5B9FC01B2EBE6B": "e059ac54e6300bea91b92ad5524c862af027166f4bf8ce0969b5a18929e57b80",
    "4C3D87E8FFF86A40FF809F241ACAB9A6": "97390edf62e37c41ae37a1686740ef5f53c8636266b46cd794fa2749caf7f726",
    "860EC8445714FFEFFF04FB50B205F7B5": "dde1101b7b9750fbb4c73389cf4d7d4802d61b4568a6bfaaa33ee55836aad25c",
    "885887A2FFD18A37FF6FFD30FDC4D77C": "5a4b3ba89d52037a604690cc6292e1005e4d574c3864747d2972235c470fad1f",
    "885887A2FFD58A33FF61FEC7FE19D52E": "4582181ecde39471e6ba7178fee15c1eed4703b167de498fff64902dabbd6a7b",
    "885887A2FFE58A03F8ADFC69F798D4E7": "24ed118318786143f0460effabbde74a31105500982d6897cb1b78033ce0d0c4",
    "885887A2FFE98A0EF894F5B7FE60DC11": "756fc6f081b23df87e31a1918bbc4f47e4c042e179323b6ed78ab2cbbf756f94",
    "885887A2FFEC8A0AF8B7FA74F4D6CB66": "b2bd747800d0c59de3a08afcda5fdcad0927217fe70a550ea11d57828ce4bd30",
    "885887A2FFEC8A0AFF00FDB9FCD1D34A": "bfc0ea462e2ffef658b4c532b590aab6dbe71de5802d951905230ae123492019",
    "885887A2FFEE8A08F8B6FB8EF622D41C": "975367aa84b958388f62f1af7170d885ab6fb33e98c618df051ff7ea065b4971",
    "885887A2FFEE8A08FF0BF632F502DAA0": "d15212f85b0639e2b2bf3d246c529d9435550fe35ae4b704e487a469b2262d75",
    "885887A2FFEF8A08F8ADF66FFC95D040": "24104fc86e597f42e066f36817bfb6236ccff859d559486dafcb5bf26bc03ece",
    "885887A2FFEF8A09FF7EF311F69DD03C": "1bdeab18482c103c3320679514261bdc3c963d21bc0487d2aa62c10e12b5b9c1",
    "885887A2FFFA8A1CFF03FEF1FCCAD36A": "a15fd8615d439ba9e3fd3d4ba627f3219ce246fa7eb4cef54fb407d8fb6d1cdf",
    "885887A2FFFB8A1DFF7CF5D2F77FDCC8": "4dcecb5d875fa266b452ceff2ef537b327430ab0013555fdee67a676601e2fb1",
    "885887A2FFFC8A1DF84DEF93FABED367": "d815c29c83798bf522200a1cba6d9ab377a615497d8206fd1f15d2dd1c4d1fdc",
    "885887A2FFFD8A1AF895F4F4FAE9DA4A": "af5f3893caeb20efbebf58c4e0db7078a5253350eb94fed5a0975fee574991f5",
    "885887A2FFFD8A1BFF66EE25F47BD385": "09aa968947d4801cb0f756ca2095956878bb6b47a78bbb24af47bd71bad30e85",
    "885887A2FFFF8A18F894F3EDFACDD152": "ec897bbe59be84ce4f724c729f881002790647d4c58b16d5345db2cbf4d8108d",
    "C13F1641FF8EFFE1FFACF513F9B2618E": "461da896d3b59152d7a805118d8da7b5772826c609458e551dd50879e60c7ed0",
    "E84887F9FFC4D64A0ACFF2EA1B00305A": "0a87cde960c0f1eceff0ca026d0d643cde1e3a1be7460d9218a87bdc76e25de8",
    "E84887F9FFC4D64A0FC8F960189C3B9A": "d5760763af511eaf81d7a04bf96284440c36d65629e45beb6ae9617a3f0d4b86",
    "E84887F9FFC6D6480FC9FE281B1D31BC": "42631b6470839105054166e28f85cd8dbe84fe81f15478cb0ae80669c4f1c1b3",
    "E84887F9FFC6D6490FCCF80314203471": "06195b520dba1e349287a7a72b440dd844f0146bf9e58136b2e7136c55533419",
    "E84887F9FFC7D64A0FD7F3D310EE30A0": "0fa85cd3ea16c6fe3c87962d724da38fc46dbc8141bf6b965b1a7222ed318b94",
    "E84887F9FFD1D6500AF7F98A10E337E2": "d0e805849ad914a48ef1fa68e7fbcfbd093e2934a7bfb3919e083b9325b6f4ec",
    "E84887F9FFD2D65C0ADAFAC610813B9C": "efa4042448d8fafe05e62b1fba969613fa850eb9d29d0b75758bd408c0883d5e",
    "E84887F9FFD9D6480FE0F4E910AF30A2": "972bb6c85aae8c683aba1d7a70f495bb24905556b4fd19ff5a7d79646537d11d",
    "E84887F9FFD9D6570FE0FD34165D3CA2": "e377eef88a6291b3056d49303334eea00c41d02546a5d789306222a0d53ca7f8",
    "E84887F9FFDAD6550F2FF66C159D359D": "462eb46c8678f7ebd62b85d24349bf6be7d565ae41990c3cd25b2cb201c00e4a",
    "E84887F9FFDED6500ACEFDA819B834FD": "c582104462bae3526290bf7daecc7cc2f0a049b7172c93dbb030a5d57a754b28",
    "E84887F9FFDFD6520FEEF7791787359A": "1647ab92f13c4b7f5477481a74bf9243e03a5653b9fd47244d9ffe9707617578",
    "4C3D87E8FF806A38FA8B9E261ACFB9C3": "47da3f87f6a79644553721c14e586b425b876ce9179bb7ab856188ba5c5e2520",
    "4C3D87E8FF816A3EFA52903B1777B75C": "4b240ccf19fbfe5d9e79c4250c0d24a67688a1a3d64be02bf055fd0015d3b467",
    "4C3D87E8FF816A3EFF4E92B91D22B06B": "a23a19f196234c2ce5bfacacf8b2a5fea744c8ba9e8ab0eb0c2513bee9f2c3d2",
    "4C3D87E8FF826A3DFF829AE519D7B3D3": "47bb1ae894b36d021be31b33771daebc0e2bc4cfa06a30f4f4d47d9e049f5b65",
    "4C3D87E8FF826A3EFA859F761F50BFA3": "9ab66de355a7a11653d23939f6c2f45c85c262b8e63683f613fcfc90ee63af2c",
    "4C3D87E8FF836A3CFF5A9AC1169BBD78": "31d7c1b3d028b48151937aa0cb8b0c78f43a0c821474f1ad6a8000123790a6cb",
    "4C3D87E8FF8C6A33FA8393FB1437B6BA": "f7fe30b4a6de7d3d792d158bee7b501543406b0e62ae75fd89fffda5d8816c9a",
}
METHODS = {"hmw-2019": "hmw-2019-compiled", "colombo-2018-pteronotus": "colombo-2018-pteronotus-field",
           "sedlock-2020-kerivoula": "sedlock-2020-kerivoula-field"}
UNITS = {"duration": "ms", "inter_pulse_interval": "ms"}

PK, CF, CH, MX, MN, ST, EN, DU, KN = ("peak_frequency", "cf_frequency", "characteristic_frequency",
                                       "max_frequency", "min_frequency", "start_frequency",
                                       "end_frequency", "duration", "knee_frequency")
H = "hmw-2019"


def r(ref, doc, page, species, obs, parameter, statistic, value=None, low=None, high=None, *,
      verbatim, sd=None, harmonic="", country="", locality="", condition="unspecified",
      n="", flag="ok", note="", printed="", variant="", variant_label=""):
    return dict(ref=ref, doc=doc, page=page, species=species, obs=obs, parameter=parameter,
                statistic=statistic, value=value, low=low, high=high, sd=sd, harmonic=harmonic,
                country=country, locality=locality, condition=condition, n=n, flag=flag,
                verbatim=verbatim, note=note, printed=printed, variant=variant,
                variant_label=variant_label)


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


# --- Call-gap search, November 2026 -------------------------------------------
# HMW accounts of species with no call in the dataset, found by
# data/calls/search_call_gaps.py (plazi pass) and read sentence by sentence.
# Left out on reading, with the reason in data/calls/search_decisions.csv:
# Mops solomonis and Macronycteris cryptovalorona (HMW: call unknown),
# Rhinolophus achilles (the Queensland values belong to R. philippinensis
# forms), Chilonatalus micropus (a prediction from ear size), Scotophilus
# borbonicus (an unidentified "Chiroptera sp1"), Molossus alvarezi and
# Philetor brachypterus (an unnamed "frequency" and a mean frequency, neither
# a registry parameter).

def hm(doc, species, obs, parameter, statistic, value=None, low=None, high=None, **kw):
    return r(H, doc, None, species, obs, parameter, statistic, value, low, high, **kw)


IP = "inter_pulse_interval"
ROWS += [
    hm("03D587F2FFC14C0AFF113AAFF5B6F633", "Coleura kibomalandy", "a", PK, "range", None, 30.6, 35.9, harmonic="1", country="Madagascar",
       verbatim="first harmonic peak frequencies of 30-6-35-9 kHz [30.6–35.9]"),
    hm("03D587F2FFC14C0AFF113AAFF5B6F633", "Coleura kibomalandy", "a", DU, "range", None, 2.5, 5.3, country="Madagascar",
       verbatim="short durations of 2-5-5-3 milliseconds [2.5–5.3]"),
    hm("03D587F2FFC34C08FF0337D6FEFCF45F", "Emballonura serii", "a", PK, "species_summary", 45, harmonic="2",
       verbatim="Greatest energy of echolocation call is 45 kHz in second harmonic"),
    hm("03D587F2FFCA4C02F82F3255F947FAAB", "Taphozous australis", "a", CH, "range", None, 23, 27, country="Australia",
       verbatim="characteristic frequencies are 23—27 kHz"),
    hm("03B0BC062412FFD4FF31EC79FBA6F24C", "Myzopoda schliemanni", "a", PK, "approximate", 46.5, country="Madagascar",
       verbatim="maximum energy at ¢.46-5 kHz [46.5]"),
    hm("03A687BCFFBBFFBA138DF33DFB38FF43", "Micronycteris microtis", "a", MN, "species_summary", 68.6,
       verbatim="multiharmonic echolocation calls of 68:6-143-3 kHz [68.6]", note="Calls of hovering bats."),
    hm("03A687BCFFBBFFBA138DF33DFB38FF43", "Micronycteris microtis", "a", MX, "species_summary", 143.3,
       verbatim="multiharmonic echolocation calls of 68:6-143-3 kHz [143.3]", note="Calls of hovering bats."),
    # Miniopterus: HMW's Malagasy accounts follow one template
    *[hm(doc, sp, "a", p, "range", None, lo, hi, country=c, verbatim=v) for doc, sp, c, rows in [
        ("E84887F9FFD9D6570FE0FD34165D3CA2", "Miniopterus aelleni", "Madagascar", [
            (PK, 50.7, 55.5, "peak frequencies of 50-7-55-5 kHz [50.7–55.5]"),
            (MX, 62.3, 79.6, "maximum frequencies of 62:3-79-6 kHz [62.3–79.6]"),
            (MN, 47.7, 51.2, "minimum frequencies of 47.7-51-2 kHz [47.7–51.2]"),
            (DU, 2.2, 4.8, "durations of 2:2—4-8 milliseconds [2.2–4.8]"),
            (IP, 42, 95.5, "intervals of 42-95-5 milliseconds [42–95.5]")]),
        ("E84887F9FFC6D6490FCCF80314203471", "Miniopterus ambohitrensis", "Madagascar", [
            (PK, 53.1, 55.4, "peak frequencies of 53-1-55-4 kHz [53.1–55.4]"),
            (MX, 64, 78.2, "maximum frequencies of 64-78-2 kHz [64–78.2]"),
            (MN, 47.7, 51.6, "minimum frequencies of 47-7-51-6 kHz [47.7–51.6]"),
            (DU, 2.5, 3.4, "durations of 2-5-3-4 milliseconds [2.5–3.4]"),
            (IP, 61.4, 73.4, "intervals of 61-4-73-4 milliseconds [61.4–73.4]")]),
        ("E84887F9FFC6D6480FC9FE281B1D31BC", "Miniopterus brachytragos", "Madagascar", [
            (PK, 57.3, 61.7, "peak frequencies of 57-3— 61-7 kHz [57.3–61.7]"),
            (MX, 85, 128, "maximum frequencies of 85-128 kHz"),
            (MN, 54, 57, "minimum frequencies of 54-57 kHz"),
            (DU, 2.6, 4.3, "durations of 2-6—4-3 milliseconds [2.6–4.3]"),
            (IP, 56.1, 122.5, "intervals of 56-1-122-5 milliseconds [56.1–122.5]")]),
        ("E84887F9FFC4D64A0FC8F960189C3B9A", "Miniopterus griffithsi", "Madagascar", [
            (PK, 43.5, 45.3, "peak frequencies of 43-5—45-3 kHz [43.5–45.3]"),
            (MX, 61, 99, "maximum frequencies of 61-99 kHz"),
            (DU, 2.9, 3.6, "durations of 2-9-3-6 milliseconds [2.9–3.6]"),
            (IP, 56.4, 128.5, "intervals of 56-4—128-5 milliseconds [56.4–128.5]")]),
        ("E84887F9FFD9D6480FE0F4E910AF30A2", "Miniopterus griveaudi", "Madagascar", [
            (PK, 56.4, 62.4, "peak frequencies of 56-4-62-4 kHz [56.4–62.4]"),
            (MX, 82, 130, "maximum frequencies of 82-130 kHz"),
            (MN, 53, 58, "minimum frequencies of 53-58 kHz"),
            (DU, 2.7, 4.4, "durations of 2.7—4-4 milliseconds [2.7–4.4]"),
            (IP, 40, 123.6, "intervals of 40—123-6 milliseconds [40–123.6]")]),
        ("E84887F9FFDFD6520FEEF7791787359A", "Miniopterus maghrebensis", "", [
            (PK, 51, 54.8, "peak frequencies of 51-54-8 kHz [51–54.8]"),
            (ST, 63.6, 101.1, "initial frequencies of 63-6-101-1 kHz [63.6–101.1]"),
            (EN, 48.9, 51.8, "end frequencies of 48-9-51-8 kHz [48.9–51.8]"),
            (DU, 3.2, 5.6, "durations of 3-2-5-6 milliseconds [3.2–5.6]"),
            (IP, 67.2, 239.2, "intervals of 67-2-239-2 milliseconds [67.2–239.2]")]),
        ("E84887F9FFC4D64A0ACFF2EA1B00305A", "Miniopterus mahafaliensis", "Madagascar", [
            (PK, 57.3, 62.2, "peak frequencies of 57-3-62-2 kHz [57.3–62.2]"),
            (MX, 95, 123, "maximum frequencies of 95-123 kHz"),
            (MN, 53, 57, "minimum frequencies of 53-57 kHz"),
            (DU, 2.9, 3.8, "durations of 2-9-3-8 milliseconds [2.9–3.8]"),
            (IP, 43.5, 95.3, "intervals of 43-5-95-3 milliseconds [43.5–95.3]")]),
        ("E84887F9FFDAD6550F2FF66C159D359D", "Miniopterus newtoni", "São Tomé and Príncipe", [
            (PK, 53.2, 61, "peak frequencies of 53-2— 61 kHz [53.2–61]"),
            (MX, 69.6, 119, "maximum frequencies of 69-6-119 kHz [69.6–119]"),
            (MN, 47.8, 52.2, "minimum frequencies of 47-8-52-2 kHz [47.8–52.2]"),
            (DU, 2.3, 7.8, "durations of 2-3-7-8 milliseconds [2.3–7.8]"),
            (IP, 31.8, 105.7, "intervals of 31-8-105-7 milliseconds [31.8–105.7]")]),
        ("E84887F9FFDED6500ACEFDA819B834FD", "Miniopterus pallidus", "", [
            (PK, 55.5, 57.9, "peak frequencies of 55-5-57-9 kHz [55.5–57.9]"),
            (ST, 58.5, 60.5, "start frequencies of 58:5-60-5 kHz [58.5–60.5]"),
            (EN, 30, 56.4, "end frequencies of 30-56-4 kHz [30–56.4]"),
            (DU, 4.8, 6.2, "durations of 4-8—6-2 milliseconds [4.8–6.2]"),
            (IP, 36.7, 109.3, "intervals of 36-7-109-3 milliseconds [36.7–109.3]")]),
        ("E84887F9FFC7D64A0FD7F3D310EE30A0", "Miniopterus sororculus", "Madagascar", [
            (PK, 53.9, 56.6, "peak frequencies of 53-9-56-6 kHz [53.9–56.6]"),
            (MX, 83, 121, "maximum frequencies of 83-121 kHz"),
            (MN, 50, 53, "minimum frequencies of 50-53 kHz"),
            (DU, 2.7, 3.9, "durations of 2:7-3-9 milliseconds [2.7–3.9]"),
            (IP, 50.8, 99.8, "intervals of 50-8-99-8 milliseconds [50.8–99.8]")]),
    ] for p, lo, hi, v in rows],
    hm("E84887F9FFC4D64A0FC8F960189C3B9A", "Miniopterus griffithsi", "a", MN, "species_summary", 40, country="Madagascar",
       verbatim="minimum frequency of 40 kHz"),
    hm("E84887F9FFD2D65C0ADAFAC610813B9C", "Miniopterus eschscholtzii", "a", MN, "mean", 45.6,
       verbatim="mean minimum frequency is 45-6 kHz [45.6]"),
    *[hm("E84887F9FFD1D6500AF7F98A10E337E2", "Miniopterus orianae", ssp, KN, "range", None, lo, hi,
         verbatim=v, note=f"Subspecies {ssp}.") for ssp, lo, hi, v in [
        ("orianae", 50.1, 51.8, "frequency of the knee ... orianae ... 50-1-51-8 kHz [50.1–51.8]"),
        ("bassanii", 48.6, 49, "bassanii ... 48-6—-49 kHz [48.6–49]"),
        ("oceanensis", 45.7, 46, "oceanensis ... 45-7-46 kHz [45.7–46]")]],
    hm("194287C9FFA8BA04B49CFA5BBABDF6D8", "Cynomops freemani", "a", EN, "mean", 22, sd=2.5, variant="low", variant_label="Low QCF call",
       verbatim="The mean end frequency of low QCF calls is 22 kHz (+ 2.5 kHz SD )"),
    *[hm("194287C9FFB4BA18B49BFDA6BB02F922", "Molossus sinaloae", v, EN, "approximate", val, variant=v, variant_label=lab,
         verbatim=f"{lab} has final frequency of ¢.{val} kHz") for v, lab, val in [("first", "First call", 30), ("second", "Second call", 40)]],
    *[hm("194287C9FFBABA17B19CF05FB007FC93", "Molossus tropidorhynchus", v, PK, "mean", val, variant=v, variant_label=lab,
         printed="Molossus milleri", verbatim=t) for v, lab, val, t in [
        ("first", "First call", 34.1, "First signal has lower frequency (mean peak frequency of 34-1 kHz) [34.1]"),
        ("second", "Second call", 39, "second call has higher frequency (mean peak frequency of 39 kHz)")]],
    hm("194287C9FFA2BA0EB498FA6BBB40F839", "Mops atsinanana", "a", PK, "species_summary", 28, country="Madagascar", printed="Chaerephon atsinanana",
       verbatim="low peak frequency (frequency with most energy) of 28 kHz", note="Russ and colleagues (2003), open environment."),
    hm("194287C9FFA2BA0EB498FA6BBB40F839", "Mops atsinanana", "a", DU, "species_summary", 8, country="Madagascar", printed="Chaerephon atsinanana",
       verbatim="a duration of 8 milliseconds", note="Russ and colleagues (2003), open environment."),
    hm("194287C9FFA3BA0FB1A5F213BBB4F373", "Mops bregullae", "a", MX, "approximate", 35, printed="Chaerephon bregullae",
       verbatim="distinctive echolocation call between 35 kHz and 20 kHz"),
    hm("194287C9FFA3BA0FB1A5F213BBB4F373", "Mops bregullae", "a", MN, "approximate", 20, printed="Chaerephon bregullae",
       verbatim="distinctive echolocation call between 35 kHz and 20 kHz"),
    hm("194287C9FF88BA24B481F57BB17EF4AE", "Ozimops lumsdenae", "a", PK, "approximate", 24, country="Australia",
       verbatim="relatively low (peak frequency c.24 kHz)"),
    hm("194287C9FF88BA24B484FCC5B504F726", "Ozimops petersi", "a", PK, "species_summary", 26, country="Australia", flag="definition_unstated",
       verbatim="relatively low-frequency echolocation call (26 kHz)", note="The account does not say which frequency."),
    hm("290787FFFFA71877FA149D33EF413C1D", "Natalus primus", "a", MN, "species_summary", 65, harmonic="2", country="Cuba",
       verbatim="Most energy is put into second harmonic, which is 65-115 kHz"),
    hm("290787FFFFA71877FA149D33EF413C1D", "Natalus primus", "a", MX, "species_summary", 115, harmonic="2", country="Cuba",
       verbatim="Most energy is put into second harmonic, which is 65-115 kHz"),
    # Kerivoula, Murina: HMW's Southeast Asian accounts
    hm("4C3D87E8FF716ACEFF5097451C54B350", "Kerivoula kachinensis", "a", PK, "mean", 123.9, 123, 124.9, country="Thailand", locality="Loei Province",
       verbatim="peak frequencies of 123-124-9 kHz (mean 123-9 kHz)"),
    hm("4C3D87E8FF716ACEFF5097451C54B350", "Kerivoula kachinensis", "a", DU, "range", None, 1.5, 2.3, country="Thailand", locality="Loei Province",
       verbatim="durations of 1-5-2-3 milliseconds [1.5–2.3]"),
    hm("4C3D87E8FF716ACEFA55945E17E6B279", "Kerivoula krauensis", "th", PK, "mean", 146.7, 136.8, 166.8, country="Thailand",
       verbatim="peak frequencies of 136-8-166-8 kHz (146-7 kHz)"),
    hm("4C3D87E8FF716ACEFA55945E17E6B279", "Kerivoula krauensis", "th", ST, "mean", 224.8, 205, 241, country="Thailand",
       verbatim="start frequencies of 205-241 kHz (mean 224-8 kHz)"),
    hm("4C3D87E8FF716ACEFA55945E17E6B279", "Kerivoula krauensis", "my", ST, "mean", 174, country="Malaysia", locality="Peninsular Malaysia",
       verbatim="In Peninsular Malaysia , average start frequency was 174 kHz"),
    hm("4C3D87E8FF716ACEFA55945E17E6B279", "Kerivoula krauensis", "my", EN, "mean", 50, country="Malaysia", locality="Peninsular Malaysia",
       verbatim="end frequency was 50 kHz"),
    hm("4C3D87E8FF716ACEFA55945E17E6B279", "Kerivoula krauensis", "my", DU, "mean", 2.4, country="Malaysia", locality="Peninsular Malaysia",
       verbatim="duration was 2-4 milliseconds [2.4]"),
    hm("4C3D87E8FF716ACFFA519FCD1DFEBFB9", "Kerivoula titania", "a", PK, "mean", 157, 137.7, 168.7, country="Thailand",
       verbatim="peak frequencies of 137-7-168-7 kHz (157 kHz)"),
    hm("4C3D87E8FF716ACFFA519FCD1DFEBFB9", "Kerivoula titania", "a", ST, "mean", 227, 217, 243, country="Thailand",
       verbatim="start frequencies of 217-243 kHz (mean 227 kHz)"),
    hm("4C3D87E8FF716ACFFA519FCD1DFEBFB9", "Kerivoula titania", "a", EN, "mean", 82.6, 74.8, 90, country="Thailand",
       verbatim="end frequencies of 74-8-90 kHz (82-6 kHz)"),
    *[hm("4C3D87E8FF616ADEFF78974D1DB6B31B", "Murina annamitica", "a", p, "range", None, lo, hi, country="Thailand", n="1", verbatim=v)
      for p, lo, hi, v in [(PK, 121.1, 139.8, "peak frequencies of 121-1-139-8 kHz [121.1–139.8]"),
                           (ST, 184, 194, "start frequencies of 184-194 kHz"), (EN, 41, 51, "end frequencies of 41-51 kHz"),
                           (DU, 2.4, 3.4, "durations of 2:4-3-4 milliseconds [2.4–3.4]")]],
    *[hm("4C3D87E8FF656ADBFA7D9E591DC0B97D", "Murina balaensis", sex, p, "range", None, lo, hi, country="Thailand", n="1",
         note=f"One {'male (holotype)' if sex == 'm' else 'female (paratype)'}.", verbatim=v)
      for sex, p, lo, hi, v in [
          ("m", PK, 90.7, 107.3, "peak frequencies of 90-7-107-3 kHz (male) [90.7–107.3]"),
          ("f", PK, 84.6, 95.3, "84-6-95-3 kHz (female) [84.6–95.3]"),
          ("m", ST, 145.9, 158.7, "start frequencies of 145-9-158-7 kHz (male) [145.9–158.7]"),
          ("f", ST, 159, 164, "159- 164 kHz (female)"),
          ("m", EN, 65.5, 67, "end frequencies of 65-5-67 kHz (male) [65.5–67]"),
          ("f", EN, 62, 66.9, "62-66-9 kHz (female) [62–66.9]")]],
    *[hm("4C3D87E8FF6E6AD2FA479DE01D9ABED7", "Murina feae", "a", p, "mean", val, lo, hi, verbatim=v) for p, val, lo, hi, v in [
        (PK, 132.9, 102.1, 148.1, "peak frequency 132-9 kHz (102-1-148-1 kHz) [132.9]"),
        (ST, 170.1, 161, 180, "average start frequency of 170-1 kHz (161-180 kHz) [170.1]"),
        (EN, 50.7, 34, 66, "end frequency 50-7 kHz (34-66 kHz) [50.7]"),
        (DU, 2.5, 2.4, 3.4, "duration 2-5 milliseconds (2:4-3-4 milliseconds) [2.5]")]],
    *[hm("4C3D87E8FF676AD8FF879F51198FBF79", "Murina guilleni", sex, p, "range", None, lo, hi, country="Thailand", n="2",
         note=f"Two {'males' if sex == 'm' else 'females'}.", verbatim=v) for sex, p, lo, hi, v in [
        ("m", PK, 120.1, 155.7, "peak frequencies of 120-1 155-7 kHz [120.1–155.7]"),
        ("m", ST, 175, 184, "start frequencies of 175-184 kHz"), ("m", EN, 53, 63, "end frequencies of 53-63 kHz"),
        ("f", PK, 120.7, 157.7, "peak frequencies of 120-7-157-7 kHz [120.7–157.7]"),
        ("f", ST, 159, 167, "start frequencies of 159-167 kHz"), ("f", EN, 50, 57, "end frequencies of 50-57 kHz")]],
    *[hm("4C3D87E8FF6C6AD3FF4091451447BAA0", "Murina harrisoni", "a", p, "mean", val, lo, hi, country="Vietnam", verbatim=v) for p, val, lo, hi, v in [
        (ST, 145.1, 122.2, 164.8, "average start frequency of 145-1 kHz (122-2-164-8 kHz) [145.1]"),
        (EN, 50.1, 45.8, 55.8, "end frequency 50-1 kHz (45-8-55-8 kHz) [50.1]"),
        (DU, 1.9, 1.3, 3.1, "duration 1-9 milliseconds (1-3-3-1 milliseconds) [1.9]")]],
    *[hm("4C3D87E8FF666ADAFA489FA61CE4BFF2", "Murina hkakaboraziensis", "a", p, "range", None, lo, hi, country="Myanmar", n="1",
         note="One poorly recorded call from the holotype.", verbatim=v) for p, lo, hi, v in [
        (PK, 148.5, 152.8, "peak frequencies of 148-5- 152-8 kHz [148.5–152.8]"),
        (EN, 62, 70, "end frequencies of 62-70 kHz"),
        (IP, 69.1, 75.3, "interpulse intervals of 69-1-75-3 milliseconds [69.1–75.3]")]],
    hm("4C3D87E8FF616ADEFF859E2F1636BF37", "Murina walstoni", "m", PK, "range", None, 117.2, 128, country="Thailand", locality="Kamphaeng Phet", n="1",
       verbatim="peak frequencies of 117-2-128 kHz [117.2–128]", note="One male."),
    hm("4C3D87E8FF616ADEFF859E2F1636BF37", "Murina walstoni", "f", PK, "range", None, 108.8, 113.7, country="Thailand", locality="Loei", n="1",
       verbatim="peak frequencies of 108-8— 113-7 kHz [108.8–113.7]", note="One female."),
    # Myotis
    hm("4C3D87E8FF386A87FA8495181BBFB152", "Myotis annatessae", "a", PK, "range", None, 45, 50, country="Vietnam",
       verbatim="peak frequencies of 45-50 kHz ( Vietnam )"),
    hm("4C3D87E8FF3C6A83FF72975E17F9BAE5", "Myotis annectans", "a", ST, "approximate", 80, country="Cambodia", verbatim="started at c.80 kHz"),
    hm("4C3D87E8FF3C6A83FF72975E17F9BAE5", "Myotis annectans", "a", EN, "species_summary", 30, country="Cambodia", verbatim="swept down to 30 kHz"),
    hm("4C3D87E8FF3C6A83FF72975E17F9BAE5", "Myotis annectans", "a", DU, "range", None, 2.1, 2.8, country="Cambodia",
       verbatim="durations 2:1-2-8 milliseconds [2.1–2.8]"),
    hm("4C3D87E8FF326A8DFF869A0718EBB150", "Myotis peytoni", "a", ST, "approximate", 85, country="India", verbatim="start at ¢.85 kHz"),
    hm("4C3D87E8FF326A8DFF869A0718EBB150", "Myotis peytoni", "a", EN, "range", None, 40, 45, country="India", verbatim="sweep down to ¢.40-45 kHz"),
    hm("4C3D87E8FF326A8DFF869A0718EBB150", "Myotis peytoni", "a", DU, "range", None, 1.5, 4, country="India",
       verbatim="Calls last 1-5-4 milliseconds [1.5–4]"),
    hm("4C3D87E8FF376A88FF5B95201C39B20B", "Myotis phanluongi", "a", PK, "range", None, 42, 45, country="Vietnam", locality="Khanh Hoa and Lam Dong",
       verbatim="peak frequencies of 42-45 kHz ( Khanh Hoa and Lam Dong )"),
    hm("4C3D87E8FF376A88FF5B95201C39B20B", "Myotis phanluongi", "b", PK, "species_summary", 60, country="Vietnam", locality="Loc Bao",
       verbatim="60 kHz (Loc Bao)"),
    hm("4C3D87E8FF536AEDFA4B91961C1EB82A", "Myotis planiceps", "a", ST, "range", None, 80, 90, country="Mexico", condition="flight_room",
       verbatim="swept from 80-90 kHz at the beginning of the call", note="Bats flying indoors."),
    hm("4C3D87E8FF536AEDFA4B91961C1EB82A", "Myotis planiceps", "a", EN, "range", None, 40, 42, country="Mexico", condition="flight_room",
       verbatim="to 40-42 kHz at the end", note="Bats flying indoors."),
    hm("4C3D87E8FF536AEDFA4B91961C1EB82A", "Myotis planiceps", "a", DU, "range", None, 2, 3, country="Mexico", condition="flight_room",
       verbatim="short (2-3 milliseconds)", note="Bats flying indoors."),
    hm("4C3D87E8FF436AFCFA52936D161AB625", "Myotis sibiricus", "a", PK, "range", None, 32, 45, flag="suspect",
       verbatim="apparently with peak frequencies of 32-45 kHz", note="HMW hedges it: 'apparently'."),
    hm("4C3D87E8FF566AE9FF8791F21903B086", "Myotis vivesi", "a", ST, "species_summary", 45, country="Mexico", verbatim="descending FM sweeps from 45 kHz to 20 kHz"),
    hm("4C3D87E8FF566AE9FF8791F21903B086", "Myotis vivesi", "a", EN, "species_summary", 20, country="Mexico", verbatim="descending FM sweeps from 45 kHz to 20 kHz"),
    hm("4C3D87E8FF566AE9FF8791F21903B086", "Myotis vivesi", "a", DU, "species_summary", 3, country="Mexico", verbatim="duration of 3 milliseconds"),
    # Lasiurus: HMW's Caribbean and South American accounts share a template
    *[hm(doc, sp, "a", p, "approximate", val, verbatim=v) for doc, sp, rows in [
        ("4C3D87E8FF836A3CFF5A9AC1169BBD78", "Lasiurus atratus", [(DU, 7.1, "last ¢.7-1 milliseconds [7.1]"), (EN, 34, "toc.34 kHz")]),
        ("4C3D87E8FF816A3EFF4E92B91D22B06B", "Lasiurus castaneus", [(DU, 6.3, "c.6-3 milliseconds [6.3]"), (ST, 53, "sweep from ¢.53 kHz"), (EN, 30, "to ¢.30 kHz")]),
        ("4C3D87E8FF816A3EFA52903B1777B75C", "Lasiurus degelidus", [(DU, 7.2, "¢.7-2 milliseconds [7.2]"), (ST, 52.5, "sweep from ¢.52-5 kHz [52.5]"), (EN, 34.5, "to c.34-5 kHz [34.5]")]),
        ("4C3D87E8FF806A38FA8B9E261ACFB9C3", "Lasiurus insularis", [(DU, 5.9, "c.5-9 milliseconds [5.9]"), (ST, 54, "sweep from c.54 kHz"), (EN, 29, "to ¢.29 kHz")]),
        ("4C3D87E8FF826A3EFA859F761F50BFA3", "Lasiurus minor", [(DU, 6.4, "c.6-4 milliseconds [6.4]"), (ST, 51, "sweep from c.51 kHz"), (EN, 29, "to ¢.29 kHz")]),
        ("4C3D87E8FF8C6A33FA8393FB1437B6BA", "Lasiurus pfeifferi", [(DU, 7.1, "(c.7-1 milliseconds) [7.1]"), (ST, 56, "sweep from ¢.56 kHz"), (EN, 26, "to ¢.26 kHz")]),
        ("4C3D87E8FF826A3DFF829AE519D7B3D3", "Lasiurus varius", [(ST, 52, "sweep from c¢.52 kHz"), (EN, 33, "to ¢.33 kHz"), (IP, 216, "interpulse intervals of ¢.216 milliseconds")]),
    ] for p, val, v in rows],
    hm("4C3D87E8FF8D6A33FA579EC91D96BEE5", "Lasiurus semotus", "a", PK, "species_summary", 27.8, country="United States", locality="Hawaii",
       verbatim="maximum spectral intensity at 27-8 kHz [27.8]"),
    hm("4C3D87E8FF8D6A33FA579EC91D96BEE5", "Lasiurus semotus", "a", ST, "species_summary", 37.1, country="United States", locality="Hawaii",
       verbatim="frequency modulation from 37-1 kHz to 25-4 kHz [37.1]"),
    hm("4C3D87E8FF8D6A33FA579EC91D96BEE5", "Lasiurus semotus", "a", EN, "species_summary", 25.4, country="United States", locality="Hawaii",
       verbatim="frequency modulation from 37-1 kHz to 25-4 kHz [25.4]"),
    # other vespertilionids
    hm("4C3D87E8FFBE6A01FF87936417F4BE28", "Arielulus circumdatus", "vn", PK, "range", None, 35, 40, country="Vietnam",
       verbatim="In Vietnam , echolocation calls were shallow FM with maximum energy at 35-40 kHz"),
    hm("4C3D87E8FFAD6A12FF449168192DB80B", "Neoeptesicus diminutus", "a", PK, "approximate", 66, printed="Eptesicus diminutus",
       verbatim="frequency of maximum energy is c.66 kHz"),
    hm("4C3D87E8FFAD6A12FF449168192DB80B", "Neoeptesicus diminutus", "a", MX, "approximate", 80, printed="Eptesicus diminutus",
       verbatim="high frequencies of ¢.80 kHz"),
    hm("4C3D87E8FFAD6A12FF449168192DB80B", "Neoeptesicus diminutus", "a", MN, "approximate", 40, printed="Eptesicus diminutus",
       verbatim="low frequencies of c.40 kHz"),
    hm("4C3D87E8FFAD6A12FF449168192DB80B", "Neoeptesicus diminutus", "a", DU, "approximate", 1.8, printed="Eptesicus diminutus",
       verbatim="Calls are c.1-8 milliseconds in duration [1.8]"),
    *[hm("4C3D87E8FFED6A52FF4895151B5EB694", "Alionoctula ceylonica", "a", p, "mean", val, lo, hi, country="India", locality="southern India",
         printed="Pipistrellus ceylonicus", verbatim=v) for p, val, lo, hi, v in [
        (PK, 44, 41.3, 49.9, "frequencies of maximum energy of 41-3-49-9 kHz (44 kHz)"),
        (MX, 101.7, 98.7, 103.8, "maximum frequencies of98-7-103-8 kHz (average 101-7 kHz) [101.7]"),
        (MN, 32.8, 32.4, 33.3, "minimum frequencies of 32-4-33-3 kHz (32-8 kHz) [32.8]"),
        (DU, 1.4, 1.1, 1.9, "durations of 1-1-1-9 milliseconds (1-4 milliseconds) [1.4]")]],
    hm("4C3D87E8FFE36A5CFF4B951F1D2AB15B", "Alionoctula collina", "a", CH, "species_summary", 40, printed="Pipistrellus collinus",
       verbatim="characteristic frequency of 40 kHz"),
    hm("4C3D87E8FFEE6A52FA97928D1A44B831", "Alionoctula coromandra", "vn", PK, "range", None, 40, 42, country="Vietnam", printed="Pipistrellus coromandra",
       verbatim="maximum energy at ¢.40-42 kHz in Vietnam"),
    *[hm("4C3D87E8FFEE6A52FA97928D1A44B831", "Alionoctula coromandra", "in", p, "mean", val, lo, hi, country="India", locality="southern India",
         printed="Pipistrellus coromandra", verbatim=v) for p, val, lo, hi, v in [
        (PK, 50.2, 47.3, 56.5, "frequencies of maximum energy of 47-3— 56-5 kHz (50-2 kHz) [50.2]"),
        (MX, 122.8, 115.7, 127.6, "maximum frequencies of 115-7-127-6 kHz (average of 122-8 kHz) [122.8]"),
        (MN, 38.8, 35.9, 43.1, "minimum frequencies of 35-9-43-1 kHz (38-8 kHz) [38.8]"),
        (DU, 1.6, 1.2, 2.1, "durations of 1-2-2-1 milliseconds (1-6 milliseconds) [1.6]")]],
    hm("4C3D87E8FFE86A57FA8A9061193AB7A3", "Alionoctula dhofarensis", "a", PK, "mean", 42.9, 37.8, 48.6, country="Oman", printed="Pipistrellus dhofarensis",
       verbatim="peak frequencies of 37-8-48-6 kHz (mean 42-9 kHz) [42.9]"),
    *[hm("4C3D87E8FFE86A57FA8A9061193AB7A3", "Alionoctula dhofarensis", "a", p, "range", None, lo, hi, country="Oman", printed="Pipistrellus dhofarensis",
         verbatim=v) for p, lo, hi, v in [(ST, 46.8, 76.7, "start frequencies of 46-8-76-7 kHz [46.8–76.7]"),
                                          (EN, 36.1, 46.2, "end frequencies of 36-1-46-2 kHz [36.1–46.2]"),
                                          (DU, 2.9, 9.6, "durations of 2:9-9-6 milliseconds [2.9–9.6]")]],
    *[hm("4C3D87E8FFF56A4AFA58977D1959B266", "Pipistrellus creticus", "a", p, "mean", val, lo, hi, country="Greece", locality="Crete", verbatim=v)
      for p, val, lo, hi, v in [(ST, 59.5, 46.2, 101.1, "Start frequency averages 59-5 kHz (46-2-101-1 kHz) [59.5]"),
                                (EN, 48.8, 43.6, 55.2, "end frequency 48-8 kHz (43-6 55-2 kHz) [48.8]"),
                                (DU, 4.3, 1.5, 8.6, "pulse duration 4-3 milliseconds (1-5-8-6 milliseconds) [4.3]")]],
    hm("4C3D87E8FFF56A4BFA5B9FC01B2EBE6B", "Pipistrellus hanaki", "a", PK, "approximate", 45, verbatim="peak frequency of c.45 kHz"),
    *[hm("4C3D87E8FFE86A57FF869F081428BEDD", "Pipistrellus raceyi", "a", p, "range", None, lo, hi, country="Madagascar", n="4", verbatim=v)
      for p, lo, hi, v in [(PK, 53.4, 58.2, "peak frequencies of 53-4-58-2 kHz [53.4–58.2]"),
                           (MX, 91.7, 128.3, "maximum frequencies of 91-:7-128-3 kHz [91.7–128.3]"),
                           (MN, 41.7, 51.4, "minimum frequencies of 41-7-51-4 kHz [41.7–51.4]"),
                           (DU, 2.3, 3.1, "durations of 2-3-3-1 milliseconds [2.3–3.1]")]],
    hm("4C3D87E8FFF86A40FF809F241ACAB9A6", "Scotoecus hirundo", "a", EN, "range", None, 30, 34, verbatim="end frequencies were 30-34 kHz",
       note="Very shallow linear FM search calls."),
    hm("4C3D87E8FFF86A40FF809F241ACAB9A6", "Scotoecus hirundo", "a", DU, "range", None, 5, 6, verbatim="call durations were ¢.5-6 milliseconds",
       note="Very shallow linear FM search calls."),
    hm("4C3D87E8FF8A6A35FF7E95A01FABB71B", "Otonycteris leucophaea", "a", PK, "range", None, 30, 32, harmonic="1", country="Kyrgyzstan",
       verbatim="lower harmonic ... maximum energy at c.30-32 kHz"),
    hm("4C3D87E8FF8A6A35FF7E95A01FABB71B", "Otonycteris leucophaea", "a", ST, "approximate", 40, harmonic="1", country="Kyrgyzstan",
       verbatim="lower harmonic had start frequency of c.40 kHz"),
    hm("4C3D87E8FF8A6A35FF7E95A01FABB71B", "Otonycteris leucophaea", "a", EN, "species_summary", 18, harmonic="1", country="Kyrgyzstan",
       verbatim="end frequency of 18 kHz"),
    *[hm("4C3D87E8FF976A28FF4C935C18A1BAE2", "Plecotus christii", "a", p, "range", None, lo, hi, verbatim=v)
      for p, lo, hi, v in [(PK, 31.4, 35.6, "Frequencies of maximum energy are 31-4-35-6 kHz [31.4–35.6]"),
                           (ST, 42.5, 48.7, "start frequencies 42-5-48-7 kHz [42.5–48.7]"),
                           (EN, 20.8, 25.7, "end frequencies 20-8-25-7 kHz [20.8–25.7]"),
                           (DU, 1.3, 1.7, "durations 1:3-1-7 milliseconds [1.3–1.7]")]],
    hm("4C3D87E8FFB96A06FF499FC51787BCF0", "Afronycteris helios", "a", ST, "approximate", 115, printed="Neoromicia helios",
       verbatim="start frequency c.115 kHz"),
    hm("4C3D87E8FFB96A06FF499FC51787BCF0", "Afronycteris helios", "a", EN, "species_summary", 65, printed="Neoromicia helios",
       verbatim="end frequency 65 kHz"),
    *[hm("4C3D87E8FFDC6A63FF7E9247180DBA6F", "Chalinolobus neocaledonicus", obs, p, "mean", val, country="New Caledonia", condition=cond,
         verbatim=v) for obs, cond, p, val, v in [
        ("fo", "unspecified", PK, 34.6, "peak frequency 34-6 kHz [34.6]"), ("fo", "unspecified", MX, 46.3, "average maximum frequency 46-3 kHz [46.3]"),
        ("fo", "unspecified", MN, 33.1, "minimum frequency 33-1 kHz [33.1]"), ("fo", "unspecified", DU, 10, "call duration 10 milliseconds"),
        ("hr", "hand_release", PK, 39.5, "peak frequency 39-5 kHz [39.5]"), ("hr", "hand_release", MX, 76.1, "average maximum frequency of 76-1 kHz [76.1]"),
        ("hr", "hand_release", MN, 28.8, "minimum frequency 28-8 kHz [28.8]"), ("hr", "hand_release", DU, 2, "call duration 2 milliseconds")]],
    hm("4C3D87E8FFC86A77FA80932416A8B77E", "Hypsugo lanzai", "a", PK, "range", None, 45, 47, country="Yemen", locality="Socotra", flag="taxon_uncertain",
       verbatim="Calls from Socotra with peak frequencies of 45-47 kHz are assumed to refer to this species",
       note="HMW: the calls are only assumed to be of this species."),
    *[hm("4C3D87E8FFC26A7DFF8A9FD918CEBFD4", "Neoromicia bemainty", "a", p, "range", None, lo, hi, country="Madagascar", printed="Hypsugo bemainty",
         verbatim=v) for p, lo, hi, v in [(PK, 49.3, 51.2, "peak frequencies 49-3-51-2 kHz [49.3–51.2]"),
                                          (ST, 69, 120.6, "start frequencies of 69-120-6 kHz [69–120.6]"),
                                          (EN, 28, 46.8, "end frequencies 28-46-8 kHz [28–46.8]"),
                                          (DU, 1.9, 4.6, "durations 1-9—4-6 milliseconds [1.9–4.6]"),
                                          (IP, 19.8, 70.2, "interpulse intervals 19-8-70-2 milliseconds [19.8–70.2]")]],
    hm("4C3D87E8FFD76A69FA5590CB1C38BF7D", "Nyctophilus daedalus", "a", PK, "mean", 52.4, 50, 54, country="Australia",
       verbatim="peak frequencies of 50-54 kHz (mean 52-4 kHz) [52.4]"),
    hm("4C3D87E8FFD06A68FA8593731B32BDF0", "Nyctophilus major", "a", PK, "mean", 44.4, 42, 47, country="Australia",
       verbatim="peak frequencies of 42-47 kHz (mean 44-4 kHz) [44.4]"),
    hm("4C3D87E8FFBB6A04FF489C8B1458BCA0", "Pseudoromicia rendalli", "a", EN, "range", None, 42, 44, country="Malawi", printed="Neoromicia rendalli",
       verbatim="end frequencies of 42-44 kHz"),
    # leaf-nosed, trident and slit-faced bats: CF and peak
    hm("03BD87A2C671A203FF3CFDBBFEF54D68", "Aselliscus dongbacanus", "a", CF, "range", None, 120.7, 133.2, harmonic="2",
       verbatim="Frequency values for the second harmonic are 120-7-133-2 kHz [120.7–133.2]"),
    hm("03BD87A2C67CA20EF89EFC3DF79F4EBC", "Hipposideros alongensis", "al", CF, "species_summary", 79.3, verbatim="79-3 kHz in alongensis [79.3]",
       note="Subspecies alongensis."),
    hm("03BD87A2C67CA20EF89EFC3DF79F4EBC", "Hipposideros alongensis", "su", CF, "species_summary", 73.3, verbatim="73-3 kHz in sungi [73.3]",
       note="Subspecies sungi."),
    hm("03BD87A2C67CA20EFF4BF595F4A8407C", "Hipposideros boeadii", "a", CF, "mean", 116.6, 114.2, 118.3, country="Indonesia",
       verbatim="frequency of maximum energy of the F portion of 116-6 kHz (114-2—118-3 kHz) [116.6]"),
    hm("03BD87A2C67DA20FFF31F64EFB1C5151", "Hipposideros griffini", "a", CF, "range", None, 76.6, 79.2, country="Vietnam", flag="definition_unstated",
       verbatim="Echolocation call frequency is c.76-6— 79-2 kHz [76.6–79.2]", note="'Call frequency' unqualified; read as the CF component."),
    hm("03BD87A2C66AA218FF5DEF31F3984475", "Hipposideros khaokhouayensis", "a", CF, "range", None, 87, 91, country="Laos", flag="definition_unstated",
       verbatim="Echolocation call frequency is 87-91 kHz", note="'Call frequency' unqualified; the description gives it as the constant frequency component."),
    hm("03BD87A2C66AA218F8ACF806F537533A", "Hipposideros kunzi", "a", CF, "range", None, 138, 144, flag="definition_unstated",
       verbatim="Echolocation call frequency is 138—144 kHz", note="'Call frequency' unqualified; read as the CF component."),
    hm("03BD87A2C672A200FF5AF605FE6052B8", "Hipposideros muscinus", "a", CF, "range", None, 89, 90, country="Papua New Guinea", flag="definition_unstated",
       printed="Doryrhina muscinus", verbatim="Echolocation call frequency is c.89— 90 kHz", note="'Call frequency' unqualified; read as the CF component."),
    hm("03BD87A2C668A21AFF50FC16FEFE4ABD", "Hipposideros orbiculus", "a", CF, "species_summary", 80, country="Malaysia", locality="Peninsular Malaysia",
       flag="definition_unstated", verbatim="In Peninsular Malaysia , call frequency of 80 kHz has been recorded",
       note="'Call frequency' unqualified; read as the CF component."),
    hm("03BD87A2C666A214FF55F782F74F4BFC", "Hipposideros pelingensis", "a", CF, "range", None, 52, 57, country="Indonesia",
       verbatim="Echolocation call includes a F component of52—57 kHz"),
    hm("03BD87A2C67DA20FF87DFECAF79849EC", "Hipposideros pendleburyi", "a", CF, "range", None, 65, 75, country="Thailand",
       verbatim="the frequency of the F part of 65-75 kHz"),
    hm("03BD87A2C669A21BF872FECBF5B74BD3", "Hipposideros rotalis", "a", CF, "range", None, 69, 71, country="Laos",
       verbatim="Call frequency of the F segment is c.69-71 kHz"),
    hm("03BD87A2C67BA20AF882F09AFA924472", "Hipposideros scutinares", "a", CF, "approximate", 63.6, flag="definition_unstated",
       verbatim="Echolocation call frequency of this species is c.63*6 kHz [63.6]", note="'Call frequency' unqualified; read as the CF component."),
    hm("03BD87A2C660A212FF52F3F7F35547D7", "Hipposideros tephrus", "a", CF, "range", None, 140, 150,
       verbatim="Echolocation call includes a F component at c.140-150 kHz"),
    hm("0383245F2225977B8BD5F631FD78FE56", "Paratriaenops auritus", "m", CF, "mean", 108.8, 106.5, 110.2, country="Madagascar",
       verbatim="CF component maximum frequencies are 106-5-110-2 kHz (mean 108 -8 kHz) in males [108.8]", note="Males."),
    hm("0383245F2225977B8BD5F631FD78FE56", "Paratriaenops auritus", "f", CF, "mean", 96.4, 95.6, 97.2, country="Madagascar",
       verbatim="95 -6-97-2 kHz (mean 96 -4 kHz) in females [96.4]", note="Females."),
    hm("0383245F222797788EC5F396F852FB4D", "Triaenops parvus", "m", PK, "mean", 93.4, 93.1, 94.2,
       verbatim="peak frequencies are 93 -1-94 -2 kHz (mean 93-4 kHz) [93.4]", note="Males."),
    hm("0383245F222797788EC5F396F852FB4D", "Triaenops parvus", "m", DU, "mean", 8, 6.6, 11.7,
       verbatim="Male calls last 6-6-11 -7 milliseconds (mean 8 milliseconds)", note="Males."),
    *[hm("860EC8445714FFEFFF04FB50B205F7B5", "Rhinopoma muscatellum", c[:2].lower(), p, "species_summary", val, harmonic="2", country=c,
         verbatim=v) for c, p, val, v in [("Iran", MN, 30, "second harmonic: 30-37 kHz in Iran"), ("Iran", MX, 37, "second harmonic: 30-37 kHz in Iran"),
                                          ("Oman", MN, 31, "31-33 kHz in Oman"), ("Oman", MX, 33, "31-33 kHz in Oman")]],
    hm("C13F1641FF8EFFE1FFACF513F9B2618E", "Cardioderma cor", "a", PK, "approximate", 49, harmonic="2",
       verbatim="peak energy in second harmonic at c.49 kHz"),
    hm("C13F1641FF8EFFE1FFACF513F9B2618E", "Cardioderma cor", "a", ST, "species_summary", 62, harmonic="2",
       verbatim="sweeping from 62 kHz to 40 kHz"),
    hm("C13F1641FF8EFFE1FFACF513F9B2618E", "Cardioderma cor", "a", EN, "species_summary", 40, harmonic="2",
       verbatim="sweeping from 62 kHz to 40 kHz"),
    # Rhinolophus: HMW's "peak F" is the peak frequency of the CF component
    hm("885887A2FFE58A03F8ADFC69F798D4E7", "Rhinolophus andamanensis", "a", PK, "mean", 57.6, 56.4, 58.5, country="India", locality="Andaman Islands",
       verbatim="peak F recorded at 56-4-58-5 kHz (mean 57-6 kHz) [57.6]"),
    hm("885887A2FFD18A37FF6FFD30FDC4D77C", "Rhinolophus chaseni", "la", PK, "range", None, 77.5, 78.5, country="Laos",
       verbatim="peak F has been recorded at 77-5-78-5 kHz in Laos [77.5–78.5]"),
    hm("885887A2FFD18A37FF6FFD30FDC4D77C", "Rhinolophus chaseni", "tn", PK, "species_summary", 80, country="Vietnam", locality="Tay Ninh",
       verbatim="at 80 kHz in Tay Ninh"),
    hm("885887A2FFD18A37FF6FFD30FDC4D77C", "Rhinolophus chaseni", "cs", PK, "species_summary", 102, country="Vietnam", locality="Con Son Island",
       verbatim="102 kHz on Con Son Island"),
    hm("885887A2FFFA8A1CFF03FEF1FCCAD36A", "Rhinolophus chiewkweeae", "a", PK, "range", None, 53.6, 54.7, country="Malaysia", locality="eastern Peninsular Malaysia",
       verbatim="peak F of 53-6-54-7 kHz [53.6–54.7]"),
    hm("885887A2FFFA8A1CFF03FEF1FCCAD36A", "Rhinolophus chiewkweeae", "a", DU, "range", None, 28.4, 63.3, country="Malaysia", locality="eastern Peninsular Malaysia",
       verbatim="duration of 28-4-63-3 milliseconds [28.4–63.3]"),
    hm("885887A2FFEE8A08FF0BF632F502DAA0", "Rhinolophus chutamasae", "m", PK, "range", None, 83.6, 87, printed="Rhinolophus monticolus",
       verbatim="peak F recorded at 83-6-87 kHz in males [83.6–87]", note="Males."),
    hm("885887A2FFEE8A08FF0BF632F502DAA0", "Rhinolophus chutamasae", "f", PK, "range", None, 91.6, 93, printed="Rhinolophus monticolus",
       verbatim="91-6-93 kHz in females [91.6–93]", note="Females."),
    hm("885887A2FFEC8A0AFF00FDB9FCD1D34A", "Rhinolophus convexus", "a", PK, "species_summary", 92, country="Laos", flag="taxon_uncertain",
       verbatim="peak F recorded at 92 kHz", note="HMW: the identity of this Lao population is uncertain."),
    hm("885887A2FFFC8A1DF84DEF93FABED367", "Rhinolophus formosae", "a", PK, "range", None, 42, 43, country="Taiwan",
       verbatim="peak F of 42-43 kHz"),
    hm("885887A2FFFC8A1DF84DEF93FABED367", "Rhinolophus formosae", "hh", PK, "range", None, 44.4, 44.6, country="Taiwan", note="Hand-held bats.",
       verbatim="aptured individuals had a peak frequency of 44-4-44-6 kHz [44.4–44.6]"),
    hm("885887A2FFFF8A18F894F3EDFACDD152", "Rhinolophus francisi", "a", PK, "range", None, 49.2, 50,
       verbatim="peak F of 49-2—50 kHz [49.2–50]"),
    hm("885887A2FFFF8A18F894F3EDFACDD152", "Rhinolophus francisi", "a", DU, "range", None, 20.2, 39.9,
       verbatim="durations of 20-2—39-9 milliseconds [20.2–39.9]"),
    hm("885887A2FFFD8A1BFF66EE25F47BD385", "Rhinolophus luctoides", "a", PK, "single", 42, country="Malaysia", locality="Cameron Highlands", n="1",
       note="One hand-held female.", verbatim="Calls from a handheld female ... had a peak F of 42 kHz"),
    hm("885887A2FFE98A0EF894F5B7FE60DC11", "Rhinolophus mcintyrei", "a", PK, "range", None, 70, 72, verbatim="peak F recorded at 70—72 kHz"),
    hm("885887A2FFD58A33FF61FEC7FE19D52E", "Rhinolophus montanus", "a", PK, "species_summary", 37, verbatim="peak F recorded at 37 kHz"),
    hm("885887A2FFFD8A1AF895F4F4FAE9DA4A", "Rhinolophus morio", "a", PK, "range", None, 40, 42, country="Malaysia", locality="Peninsular Malaysia",
       verbatim="Calls in Peninsular Malaysia had a range of peak frequencies of 40—42 kHz"),
    hm("885887A2FFEF8A08F8ADF66FFC95D040", "Rhinolophus perditus", "is", PK, "range", None, 96, 98, country="Japan", locality="Ishigakijima",
       verbatim="peak F recorded at 96-98 kHz on Ishigakÿima"),
    hm("885887A2FFEF8A08F8ADF66FFC95D040", "Rhinolophus perditus", "ir", PK, "range", None, 92, 93, country="Japan", locality="Iriomotejima",
       verbatim="92-93 kHz on Iriomotejima"),
    *[hm("885887A2FFEF8A09FF7EF311F69DD03C", "Rhinolophus pumilus", obs, PK, "mean", val, lo, hi, country="Japan", locality=loc, note=sex, verbatim=v)
      for obs, loc, sex, val, lo, hi, v in [
        ("nm", "northern Okinawajima", "Males.", 108.2, 105.6, 110.9, "males had peak frequencies of 105-6—110-9 kHz (mean of 108-2 kHz) [108.2]"),
        ("nf", "northern Okinawajima", "Females.", 110.6, 107.7, 113, "females had 107-7—113 kHz (mean of 110-6 kHz) [110.6]"),
        ("sm", "southern Okinawajima", "Males.", 116, 112.8, 119.3, "males at 112-8— 119-3 kHz (mean of 116 kHz)"),
        ("sf", "southern Okinawajima", "Females.", 117.4, 104.6, 120.1, "females at 104-6—120-1 kHz (mean of 117-4 kHz) [117.4]")]],
    hm("885887A2FFEC8A0AF8B7FA74F4D6CB66", "Rhinolophus refulgens", "m", PK, "range", None, 98.6, 105.2, verbatim="peak F reported at 98-6-105-2 kHz in males [98.6–105.2]", note="Males."),
    hm("885887A2FFEC8A0AF8B7FA74F4D6CB66", "Rhinolophus refulgens", "f", PK, "range", None, 100.7, 104.1, verbatim="100-7-104-1 kHz in females [100.7–104.1]", note="Females."),
    hm("885887A2FFEC8A0AF8B7FA74F4D6CB66", "Rhinolophus refulgens", "sg", PK, "species_summary", 97.8, country="Singapore",
       verbatim="Peak frequencies in Singapore were reported at 97-8 kHz [97.8]"),
    hm("885887A2FFEE8A08F8B6FB8EF622D41C", "Rhinolophus shortridgei", "a", PK, "range", None, 94.5, 100.7, country="Myanmar",
       verbatim="peak F recorded at 94-5-100-7 kHz in Myanmar [94.5–100.7]"),
    hm("885887A2FFFB8A1DFF7CF5D2F77FDCC8", "Rhinolophus thailandensis", "th", PK, "range", None, 49, 50.9, country="Thailand",
       verbatim="peak F recorded at 49-50-9 kHz in Thailand [49–50.9]"),
    hm("885887A2FFFB8A1DFF7CF5D2F77FDCC8", "Rhinolophus thailandensis", "kh", PK, "species_summary", 53.6, country="Cambodia",
       verbatim="53-6 kHz in Cambodia [53.6]"),
]


def num(x) -> str:
    return "" if x is None else f"{x:g}"


def reading(row) -> str:
    """The OCR text, plus the reading in brackets when the OCR hides the number
    (decimal points printed as hyphens). The builder checks the stored value
    appears in this text."""
    text = row["verbatim"]
    if row["value"] is None or "[" in text:
        return text
    # Parsed as build_calls.py does: "30-37" there reads as 30 and -37.
    plain = text.replace("–", "-").replace("−", "-")
    printed = [float(n) for n in re.findall(r"[-+]?\d+(?:\.\d+)?", plain)]
    if any(abs(n - row["value"]) < 1e-9 for n in printed):
        return text
    span = f"{row['low']:g}–{row['high']:g}; " if row["low"] is not None else ""
    return f"{text} [{span}{row['value']:g}]"


def main() -> None:
    for doc, expected in PINS.items():
        got = hashlib.sha256(xml_path(doc).read_bytes()).hexdigest()
        if got != expected:
            raise SystemExit(f"{doc}.xml: sha256 {got} does not match the pinned {expected}")
    resolver = TaxonResolver()
    # A treatment printed under an older combination (HMW's Chaerephon,
    # Pipistrellus ceylonicus ...): the current name is given beside it, and
    # was checked against the species' MDD name history.
    for row in ROWS:
        if row["printed"]:
            current, _ = resolver.resolve(row["species"])
            resolver.add_manual({row["printed"]: current["id"]})
    out, seen = {}, {}
    for row in ROWS:
        if row["doc"] not in PINS:
            raise SystemExit(f"{row['doc']} is not pinned")
        species, method = resolver.resolve(row["printed"] or row["species"])
        if species is None:
            continue
        ref = row["ref"]
        seen.setdefault(ref, set()).add(species["id"])
        label = "Table 5" if ref == "sedlock-2020-kerivoula" else "species account"
        out.setdefault(ref, []).append({
            "observation_id": f"{ref}-{species['id']}-{row['obs']}", "mdd_id": species["id"],
            "verbatim_taxon_name": row["printed"] or row["species"], "taxon_match_method": method,
            "reference_id": ref,
            "locator": f"p. {row['page'] or xml_page(row['doc'])}, {label}; Plazi treatment {row['doc']}",
            "method_id": METHODS[ref],
            "call_phase": "unspecified", "recording_condition": row["condition"],
            "call_variant": row["variant"], "variant_label": row["variant_label"],
            "country": row["country"], "locality": row["locality"], "n_individuals": row["n"],
            "parameter": row["parameter"], "statistic": row["statistic"], "value": num(row["value"]),
            "value_min": num(row["low"]), "value_max": num(row["high"]),
            "unit": UNITS.get(row["parameter"], "kHz"),
            "dispersion_type": "sd" if row["sd"] is not None else "", "dispersion_value": num(row["sd"]),
            "harmonic": row["harmonic"], "verbatim_value": reading(row), "quality_flag": row["flag"],
            "notes": row["note"],
        })
    for ref, rows in out.items():
        write_rows(ref, rows)
        write_review(ref, resolver.unresolved)
        report(ref, len(rows), len(seen[ref]), resolver)


if __name__ == "__main__":
    main()
