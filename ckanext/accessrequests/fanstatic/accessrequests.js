this.ckan.module('account-request-manage', {
  options: {
  },

  initialize: function () {
    jQuery.proxyAll(this, /_on/);
    this.el.on('click', this._onClick);
  },

  _onClick: function (event) {
    var self = this;
    var row = this.el.closest('tr');
    var action = this.options.action;
    var user_id = this.options.id;
    var user_name = this.options.name;
    jQuery.ajax(
      {
        url : this.options.href,
        type: "POST",
        data : {'action':action, 'id': user_id, 'name': user_name},
        success:function(data, textStatus, jqXHR)
        {

          if (action=='approve'){
            jQuery('.btn', row).closest('td').html('Approved. Notification has been sent to the user');
          } else {
            jQuery('.btn', row).closest('td').html('Rejected. Notification has been sent to the user');
          }
        },
        error: function(jqXHR, textStatus, errorThrown)
        {
            row.addClass('management-error');
            self.el.popover({ content: 'Error', placement: 'top'}).popover('show');
            setTimeout(function () {
              self.el.popover('destroy');
            }, 4000);
        }
      }
    );
  }

});
