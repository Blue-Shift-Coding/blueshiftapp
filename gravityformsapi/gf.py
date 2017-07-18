import os
from pygfapi import Client as GravityFormsClient

gf = GravityFormsClient(
	os.environ["BLUESHIFTAPP_GRAVITY_FORMS_BASE_URL"]+"/gravityformsapi/",
	os.environ["BLUESHIFTAPP_GRAVITY_FORMS_PUBLIC_KEY"],
	os.environ["BLUESHIFTAPP_GRAVITY_FORMS_PRIVATE_KEY"]
)