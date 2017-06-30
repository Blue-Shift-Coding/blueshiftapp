<?php
/*
Plugin Name: Blueshift
Plugin URI: http://www.blueshiftcoding.com
Description: Various functions to enable the Blueshift website
Author: Will Voelcker
Author URI: http://www.willv.net
Version: 1.0
*/

class BlueshiftPlugin {

	static public function create() {
		return new BlueshiftPlugin;
	}

	public function stopGravityFormsAPIOverridingWordpressRestAPIs() {
		if (preg_match("|^/wp-json|", $_SERVER["REQUEST_URI"])) {
			add_filter("pre_option_gravityformsaddon_gravityformswebapi_settings", function() {
				return array("enabled" => false);
			});

		}
	}

	public function init() {
		$this->stopGravityFormsAPIOverridingWordpressRestAPIs();
	}
}

BlueshiftPlugin::create()->init();
