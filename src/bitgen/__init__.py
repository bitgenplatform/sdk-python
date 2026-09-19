"""Official Python SDK for the BITGEN API v4.

```python
from bitgen import BitgenClient, Env

client = BitgenClient(scope="YOUR_SCOPE_UUID", apiKey="YOUR_API_KEY", env=Env.SANDBOX)
```
"""

from bitgen.client import BitgenClient
from bitgen.constants import Asset, Env
from bitgen.errors import BitgenError, UnexpectedAnswerError
from bitgen.page import Page
from bitgen.version import VERSION

__version__ = VERSION

__all__ = ["VERSION", "Asset", "BitgenClient", "BitgenError", "Env", "Page", "UnexpectedAnswerError"]
