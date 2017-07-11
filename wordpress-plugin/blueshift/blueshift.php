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
	private $protectedCategoryTaxonomy = "product_cat", $protectedTermName = "FILTERS";

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

	public function preventAnyoneEditingTheFiltersCategory() {
		add_action('edit_terms', function($termId, $termTaxonomyId, $taxonomySlug) {

			if ($taxonomySlug == $this->protectedCategoryTaxonomy) {
				$term = get_term_by("id", $termId, $this->protectedCategoryTaxonomy);
				if (empty($term)) {
					return;
				}

				$termObject = (object)$term;
				$termName = $termObject->name;

				// Crash out horribly if this is an attempt to edit the protected term
				if ($termName == $this->protectedTermName and empty($termObject->parent)) {
					echo "ERR: '".$this->protectedTermName."' is a system category and cannot be edited";
					exit;
				}
			}
		});
	}

	public function init() {
		$this->stopGravityFormsAPIOverridingWordpressRestAPIs();
		$this->preventAnyoneEditingTheFiltersCategory();
	}
}

BlueshiftPlugin::create()->init();
