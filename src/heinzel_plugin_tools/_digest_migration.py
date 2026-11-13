"""Pinned old-to-new gallery input digests of this repository's galleries at the ADR 0003 flip.

Each key is a digest a gallery or screenshot definition was reviewed under while the locks, the plugin version and its
dependency declarations were capture inputs; each value is the digest of the same source under the rule that leaves
them out, computed at the flip while the old digest still matched. An entry keeps exactly that reviewed source
current through a later relock, security floor or version bump; any change to what renders makes it stale.
"""

MIGRATED_DIGESTS: dict[str, str] = {
    # heinzel-atlassian gallery
    "fe5d3c8bb141ea577545d88409f8d8f16e90e440d8f5bb09a9c43450944441d3": (
        "17024838ace1566e5fc44377fa66f5339f279a7efacb53d420fdf94613e5dc8f"
    ),
    # heinzel-atlassian definition
    "40ebcebf50a155f29c12e5e0a8744b8811bd9477a0435e312ad4359e1066fb6e": (
        "db694ed471ac2559ca3ff65214365b60ed873fd18acf458813d9c09f6af9a1dd"
    ),
    # heinzel-example gallery
    "855bf3b5a71afd5ca72803e6de2a0920cdb229a90cd1dd6297525b336f353f47": (
        "f20ac885aa8857b4a71c900d245ea8a1a9b33311ac81e41586d5ab1f2ca87a62"
    ),
    # heinzel-example definition
    "50b56f504ae62164ad6841093f05abef327a6e4f5072af3d67ef62a31de2ea73": (
        "7d095b23d4f9bc8dcf8a69e08937a06f2e2f4eac5f9036e3312874a615e3f2e4"
    ),
    # heinzel-github gallery
    "fa6fe68cb794cf040f6bb7b3a86b354f6ba2587f5c2c704765cea06ad256c186": (
        "08c04176e899f460cfae519fd37bde02fbaa0d2e52d39a495ead7fa0d277eaaa"
    ),
    # heinzel-github definition
    "4965336e7284ca3f776242e2244e65d4ead21d20c813f31041c249a07e4a7293": (
        "3df64dae941306c9236e1209d49c09d0180d5b8bae63d54ac289f75b366bf475"
    ),
    # heinzel-google gallery
    "d4f75b1c9fa62f36d1668a94a403740cc27f89a7a69a7f05b1f231f7c6511679": (
        "ca04382c12e7dce80b7795d110e9ffa3267280e055781080dee0863000bd5d71"
    ),
    # heinzel-google definition
    "828eb73ece74a7b99959089fa5f4ef8df79a8ae5b252386af0a3f8583ab75446": (
        "04be9572188890bed462149f59af444ffa2390234c5f1ecffc0669bf58b60950"
    ),
    # heinzel-issues gallery
    "9560d558bc9e6a7dc1b591ee1987c724342e1f129d58564a1a59d9e21899bc48": (
        "367f938a6992d70b49184c8531ab639f5b0eeaa3f8f271734c1985931cf969e4"
    ),
    # heinzel-issues definition
    "41bec2e172687aacb4b1c86a2ce3eb1751061e615157b722a43f525295dc4569": (
        "5e98c1052bc8d8f984d9f15744aa6619786c163861eebeea085482bb23e0e8e4"
    ),
    # heinzel-resource gallery
    "f8a6b3873f8b67f3a9873c48ed5a9e5c7ae2e4a12c72ec09b7dde872ed27bd54": (
        "f33bb8f372afa81ea1964f83a02178825b718569643c3120233a5283d3fad90b"
    ),
    # heinzel-resource definition
    "de732cc7d7480bc72602985a097684d43325591e38d92fb2dd2ac89634ab39f2": (
        "10fefc026908d3ea039577a2515433b01603725cc0498f18bfef29200aa5b4e6"
    ),
    # heinzel-slack gallery
    "6188c937d7e03095803a2cebb5ca018f952a967de52712701308ac07be79a348": (
        "96ed4301574cdfe5427187f8ff5b15c56f1f81a5900662d10d91b939f92be520"
    ),
    # heinzel-slack definition
    "6657e0bf84705c1ed3e58b642b8f28acd5d4af66b03f6b8af407f6d0dcb48d39": (
        "39b835ea9af5734eb4c9fa4c22bc492c7a9da1dab550fcdac7dfa4d0ec4a7862"
    ),
    # heinzel-tailscale gallery
    "9a20c109d44d267cb0279757b972471df5e4d24535a040e6f46c08c21963f8cc": (
        "647c68e42d053a62f7d65501f5ed4d9305890858febac4ae59ca7dfd3c4ae95d"
    ),
    # heinzel-tailscale definition
    "87024d15213c3b3cb2a986ac028bf05a53c960c922b6402b9dc5ea50f220431d": (
        "84c29f9a7b8f8485a512c55f0e063d05f0ef121052ddb43450e5ed853c9d8b26"
    ),
    # heinzel-theme gallery
    "956c896460db8ead6ba2b06b98384717d5b290d2de55326b75fc95b56a791e1d": (
        "f902dce6089a42b16567aef968c9d813d4678e1049392246d9e01106b96f915c"
    ),
    # heinzel-theme definition
    "21a855cd8644a76635c5d7bf63e969dfc118da169fd80bdad7d65c4417403f11": (
        "7a513e89126812ba3a8349f6878d8c372fed71ce53522f577c9ae80b3b1909df"
    ),
    # heinzel-zoom gallery
    "f3639c7339be01a8790726f9887933e4314ba05e7efc39e3eaff26ff00057a79": (
        "60c7fbe21d96012ac1b3d8a43897ac75863a0736e3b7a50f4f58c91a2b48dc56"
    ),
    # heinzel-zoom definition
    "a554378db30fc70eb1c48381eb43a166359df6ef8f3fa77795061d76bb9d4fbe": (
        "26186149678fee990f61cb522408b308f2d7adfcfc31fc074414f9080a328a90"
    ),
}
