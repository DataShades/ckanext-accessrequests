ckan.module('bs-tooltip', function($, _) {
  'use strict';
  return {
    initialize: function() {
      $('[data-toggle=tooltip]').tooltip();
    }
  };
});
