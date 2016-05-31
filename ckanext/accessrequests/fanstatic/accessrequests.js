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
    jQuery.ajax(
      {
        url : this.options.href,
        type: "POST",
        data : {'action':action, 'id': user_id},
        success:function(data, textStatus, jqXHR) 
        {   

          if (action=='approve'){
            row.addClass('management-approve');
            jQuery('.btn', row).attr('disabled', 'disabled').removeClass('btn-info btn-success');
          } else {
            row.remove();
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
