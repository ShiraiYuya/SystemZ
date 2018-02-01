class ApplicationController < ActionController::Base
  protect_from_forgery with: :exception
  before_action :authenticate_user!
  before_action :configure_permitted_parameters, if: :devise_controller?
  
  protected
  
  def configure_permitted_parameters
      devise_parameter_sanitizer.permit(:sign_in, keys: [:name, :email, :password])
	  devise_parameter_sanitizer.permit(:sign_up, keys: [:name, :email, :password])
	  devise_parameter_sanitizer.permit(:account_update, keys: [:name, :email, :password])

  end
	
	def after_sign_in_path_for(resource)
		pages_show_path = '/users/index'
	end
end
