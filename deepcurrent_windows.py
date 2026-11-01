#!/usr/bin/env python3
# DeepCurrent Windows Test v0.1
# Reuses the frozen v5.3 browser implementation.

import sys

from deepcurrent_browser_macos_v5_3_music import main


if __name__ == "__main__":
    if sys.platform != "win32":
        print(
            "DeepCurrent Windows Test v0.1: "
            "Windows runtime required."
        )
        sys.exit(1)

    main()
