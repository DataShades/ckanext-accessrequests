ckan.module('bs-tooltip', function($, _) {
  'use strict';
  return {
    initialize: function() {
        document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(
            el => {
                console.log(el)
                new bootstrap.Tooltip(el)
            }
        )
    }
  };
});
