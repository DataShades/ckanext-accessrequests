jQuery(document).ready(function(){
  var selects = jQuery('#organization-for-request option').filter(':selected');
  for (var i = 0; i < selects.length; i++) {
    if (selects[i].hasAttribute('selected')) {
      selects[i].removeAttribute('selected');
      selects[i].setAttribute('selected', 'selected');;
    }
  }
});
