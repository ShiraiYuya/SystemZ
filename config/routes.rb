Rails.application.routes.draw do
  devise_for :users
  get 'users/index'
  get '/users/index'
  root to:'users#index'
end

# For details on the DSL available within this file, see http://guides.rubyonrails.org/routing.html
