subroutine double_moments( &
     rohydro,ntot,nu_mass,mu_mass,alpha_dm,beta_dm, &		!IN
     a_dia,lambda_dia,nu_dia,mu_dia,alpha_md,beta_md)		!OUT

  !This routine convert the parameters of a drop size distribution as a function of MASS F(m)
  !		F(m)=A_mass * m ^ Nu_mass * exp(- Lambda_mass * m ^ Mu_mass)
  !to the parameters of a drop size distribution as a function of diameter f(d)
  ! 	F(r)=A_dia * r ^ Nu_dia * exp(- Lambda_dia * d ^ Mu_dia)
  !
  !As a reference for conversion from MASS to DIAMETER see table.2 and eq.51 in
  !GW Petty and W Huang JAS, 2011
  !
  !As a reference for the calculation of a and lambda for F(m) see appendix.a Seifert and Beheng, 2006, MAP
  !
  !INPUT:
  !rohydro		: density of idrometeor 						[kg/m^3]
  !ntot			: total number concentration					[#/m^3]
  !nu_mass		: Nu parameter of F(m)
  !mu_mass		: Mu parameter of F(m)
  !alpha_dm 	: alpha parameter for diameter-mass relation	[m*kb^(-beta_dm)]
  !beta_dm		: beta parameter for diameter-mass relation
  !
  !OUTPUT
  !a_dia		: A parameter of F(d)							[#/m^(nu_dia+4)]
  !lambda_dia	: Lambda parameter of F(d)						[m^(-mu_dia)]
  !nu_dia		: Nu parameter of F(d)
  !mu_dia		: Mu parameter of F(d)
  !alpha_md		: alpha parameter for mass-diameter relation	[m*kb^(-beta_md)]
  !beta_md		: beta parameter for mass-diameter relation

  use kinds

  implicit none

  real (kind=dbl),intent(in)			:: 		rohydro,ntot,nu_mass,mu_mass,alpha_dm,beta_dm
  real (kind=dbl),intent(out)			::		a_dia,lambda_dia,nu_dia,mu_dia, alpha_md, beta_md

  real (kind=dbl)					::		a_temp, lambda_temp
  real (kind=dbl)					::		gammln
  real (kind=dbl)					::		arg1, arg2, gamma1, gamma2

  arg1=(nu_mass+1.d0)/mu_mass
  arg2=(nu_mass+2.d0)/mu_mass
  gamma1=exp(gammln(arg1))
  gamma2=exp(gammln(arg2))
  !		a and lambda of the drop size distribution as a function of MASS
  lambda_temp=(rohydro*gamma1/ntot/gamma2)**(-mu_mass)
  a_temp=ntot*mu_mass*lambda_temp**(arg1)/gamma1

  !From diameter-mass relation		to		mass-diameter
  !     D=alpha_dm * m^beta_dm		-->		m=alpha_md * D^beta_md
  beta_md=1.d0/beta_dm
  alpha_md=(1.d0/alpha_dm)**beta_md

  !a, lambda, nu, mu from the drop size distribution as a function of mass F(m) to DIAMETER F(D)
  a_dia=a_temp*alpha_md**(nu_mass+1.)*beta_md
  lambda_dia=lambda_temp*alpha_md**(mu_mass)
  mu_dia=mu_mass*beta_md
  nu_dia=beta_md*(nu_mass+1.d0)-1.d0

  return
end subroutine double_moments
