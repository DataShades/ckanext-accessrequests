jQuery(document).ready(function(){
  var orgs = $('.org-td');
  for (var i=0; i<orgs.length; i++ ) {
    var org_val = $(orgs[i]).find('#s2id_organization-for-request').text().trim();
    if (org_val == 'No organisation') {
      var role_div = $(orgs[i]).closest('tr').find('.role-td').find('#organization-role');
      $(role_div).prop("disabled", true);
    }
  }
  $(orgs).on('change', function(e) {
    var org = $(this).find('#s2id_organization-for-request').text().trim();
    var role = $(this).closest('tr').find('.role-td').find('#organization-role');
    if (org == 'No organisation') {
      $(role).prop("disabled", true);
    } else {
      $(role).prop("disabled", false);
    }
  });
});
