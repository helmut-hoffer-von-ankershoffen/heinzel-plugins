"""Pinned old-to-new gallery input digests of this repository's galleries at the ADR 0003 flip.

Each key is a digest a gallery or screenshot definition was reviewed under while the locks, the plugin version and its
dependency declarations were capture inputs; each value is the digest of the same source under the rule that leaves
them out, computed at the flip while the old digest still matched. An entry keeps exactly that reviewed source
current through a later relock, security floor or version bump; any change to what renders makes it stale.
"""

MIGRATED_DIGESTS: dict[str, str] = {
    # heinzel-atlassian gallery
    "fe5d3c8bb141ea577545d88409f8d8f16e90e440d8f5bb09a9c43450944441d3": (
        "6b3785dfcc4abfae67640d7ed9ea89d9229e517c77a708f01ae7e4d76cbf5e4a"
    ),
    # heinzel-atlassian definition
    "40ebcebf50a155f29c12e5e0a8744b8811bd9477a0435e312ad4359e1066fb6e": (
        "6d78304bb66436239718b029021a08a88ab03470e8a14a6d5e583aaa78dccda5"
    ),
    # heinzel-clock gallery
    "f3ed7f7f640daabf6095e70e0e9466254d021214395136492f778aec1d74b0a4": (
        "11edde3f40de9fdea2ba810879ef6d2365ffa1c0f8a2572015aa5af1c0294f46"
    ),
    # heinzel-clock definition
    "13230bb1b73f59c8da2bab49888185f97ac0384e309c346a62ec6be7d8e60513": (
        "a4d03f61669a9f988d57ecd76ae46a82ddad8b33d837dc5eb7b755910a2dfb9a"
    ),
    # heinzel-example gallery
    "855bf3b5a71afd5ca72803e6de2a0920cdb229a90cd1dd6297525b336f353f47": (
        "2954ef6e795d89a971c09cc4865b74b33db6c701700ddaaae1b019af51a144ec"
    ),
    # heinzel-example definition
    "50b56f504ae62164ad6841093f05abef327a6e4f5072af3d67ef62a31de2ea73": (
        "5a2a38882576130e6147fbf1e368556b120b72f5ecc91d078eaec54556a62ca4"
    ),
    # heinzel-github gallery
    "fa6fe68cb794cf040f6bb7b3a86b354f6ba2587f5c2c704765cea06ad256c186": (
        "a0ea2ffbe42179f934611d86c20067a196cae7b8f8151a58398263da39389973"
    ),
    # heinzel-github definition
    "4965336e7284ca3f776242e2244e65d4ead21d20c813f31041c249a07e4a7293": (
        "82771c8bc5fa5c4e742d11ee3885b44c3870b9c09f83fd78dd14d69522363459"
    ),
    # heinzel-google gallery
    "d4f75b1c9fa62f36d1668a94a403740cc27f89a7a69a7f05b1f231f7c6511679": (
        "204fe653226b64633cfc5ba0b97f7c81b8b9a0028ceff6602f155a1cd352cfbf"
    ),
    # heinzel-google definition
    "828eb73ece74a7b99959089fa5f4ef8df79a8ae5b252386af0a3f8583ab75446": (
        "c0b1899272d8f720135dd5a3c8150ecd0486f5ecd846371d8ab2155959b1f522"
    ),
    # heinzel-issues gallery
    "9560d558bc9e6a7dc1b591ee1987c724342e1f129d58564a1a59d9e21899bc48": (
        "143944e597cc5d7174dfe02a9d659a5ebe2745a7fdb4a336cc46bc82c3f1e939"
    ),
    # heinzel-issues definition
    "41bec2e172687aacb4b1c86a2ce3eb1751061e615157b722a43f525295dc4569": (
        "3e56b25a5088c4164b5603d9284109b433e7c63adb76c00567c6cc913e1d41e4"
    ),
    # heinzel-resource gallery
    "f8a6b3873f8b67f3a9873c48ed5a9e5c7ae2e4a12c72ec09b7dde872ed27bd54": (
        "d9b5a35b7d85564c8a6c6174195772e75927421ef403ca9c5fde019c7b7c8d7c"
    ),
    # heinzel-resource definition
    "de732cc7d7480bc72602985a097684d43325591e38d92fb2dd2ac89634ab39f2": (
        "ceeb3240bbdc03c060568f108031222ca61a845ac037ff96e6a707045899fd28"
    ),
    # heinzel-slack gallery
    "6188c937d7e03095803a2cebb5ca018f952a967de52712701308ac07be79a348": (
        "dcbcfbbdfbbe128daeb0ba8f12fbda6f43f51dc0f05aef03e6301bb6c5550982"
    ),
    # heinzel-slack definition
    "6657e0bf84705c1ed3e58b642b8f28acd5d4af66b03f6b8af407f6d0dcb48d39": (
        "212bf39e9944e7a3353bde3d1affc3e7009bc193aa7963b7c5b7ab52b6ac5e38"
    ),
    # heinzel-tailscale gallery
    "9a20c109d44d267cb0279757b972471df5e4d24535a040e6f46c08c21963f8cc": (
        "56aca97a294d2aead22db387bca7307e82f2715e4c77b41a22a7154d51e130be"
    ),
    # heinzel-tailscale definition
    "87024d15213c3b3cb2a986ac028bf05a53c960c922b6402b9dc5ea50f220431d": (
        "bdde94e472738cdf002d4d1f32f9db1662b8f96f5d2d2774bcf721e834cfff5e"
    ),
    # heinzel-theme gallery
    "956c896460db8ead6ba2b06b98384717d5b290d2de55326b75fc95b56a791e1d": (
        "327740e7e230de935c858b11ef617aa4eb2b6aec3a08ccd2cb6538157e7aba19"
    ),
    # heinzel-theme definition
    "21a855cd8644a76635c5d7bf63e969dfc118da169fd80bdad7d65c4417403f11": (
        "b07474f90bf3a509782cd494cb3fe578d83fb69cf9312018e50aa8660b02da3a"
    ),
    # heinzel-weather gallery
    "623b2fd453296f9728aaf23a97df73f5d826c7a239f0cd28617f5a3d4e3cf9eb": (
        "d417ae01414d93dbc63a85f90f5acb6ec7bc23a7a2434e62d3482ba3985749e8"
    ),
    # heinzel-weather definition
    "6007f977c8dedbba4bb3255ff3c85f81e3a3027a569fbd0834d10c41d4da2449": (
        "c03ddb944bc7bc905e1abaab0f7b99749d65917955670a37d4bc34ade437a63c"
    ),
    # heinzel-zoom gallery
    "f3639c7339be01a8790726f9887933e4314ba05e7efc39e3eaff26ff00057a79": (
        "e9cb751f1e183927796f9114622ed3c4066d7c89bd59f5c3aaff436ec8f15560"
    ),
    # heinzel-zoom definition
    "a554378db30fc70eb1c48381eb43a166359df6ef8f3fa77795061d76bb9d4fbe": (
        "f1d94d40d30ba49ce23ce460dea0dd6a7955f5dd6d56b0ae22fcd585faf742fb"
    ),
}
