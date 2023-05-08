jQuery(document).ready(function(){
  var org = $('#organization-for-request');
  var role_div = $('#role').closest('.form-group');
  if (!org.val()) {
    role_div.hide();
  }
  org.on('change', function() {
    if (org.val()) {
      role_div.show();
    } else {
      role_div.hide();
    }
  });
});
