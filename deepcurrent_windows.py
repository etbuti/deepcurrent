#!/usr/bin/env python3
# DeepCurrent Windows Test v0.1
# Reuses the frozen v5.3 browser implementation.

import sys

from deepcurrent_browser_crossplatform import main


if __name__ == "__main__":
    if sys.platform != "win32":
        print(
            "DeepCurrent Windows Test v0.1: "
            "Windows runtime required."
        )
        sys.exit(1)

    main()
