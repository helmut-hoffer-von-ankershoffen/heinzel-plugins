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
    # heinzel-google gallery
    "c55e21d8b4058694bbf28bc39e754f38a6f1f2eb27091aa70622eb018c72c91d": (
        "844a7a75738a418731ea4db1a3e298d2952cc8417c81e0855c58f6bd18c6c832"
    ),
    # heinzel-google definition
    "14628b19796d865fca67e901e4e58c42517ce9bc7970d748b80a5cb49bd28f05": (
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
    "4435860e68ad76f26997679152d2700d55f9ad7b08cbab33fa66557836e49b6c": (
        "920f79077bcedf69ee5783efaac52acba1eaa1e653fe7927c8df6e584d1323cc"
    ),
    # heinzel-slack definition
    "5a0d5a055e649e2bdc229a06cf29159f871aee3249f1bfb2ec54aef8350a6588": (
        "68db2a1dc1ae7de24a188d372a5b6e5f5cfa535decdf2b9e6fb313bc20460992"
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
    "cce74a37e74fdf7abec5b0315097e390a6328ae82319d85b750110ec157bcb2e": (
        "a51f6a789d7050ec2f3ab6f00ce6d0e925cc53768f51e5f69b9233a6fe21ebcb"
    ),
    # heinzel-zoom definition
    "29f68236570785a8787752d5bb3ebd4c2c21e31f1813869c87538d0c3c6de154": (
        "15ea60c6c3465c50c3413c80a3da4c11690a6cd0e0486ef180a0754b15a03dfa"
    ),
}
