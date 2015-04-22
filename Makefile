ARCH=$(shell uname -s)
OBJDIR := build/
SRCDIR := src/
BINDIR := bin/
LIBDIR := lib/
PYTDIR := pyPamtra/

gitHash    := $(shell git show -s --pretty=format:%H)
gitVersion := $(shell git describe)-$(shell git name-rev --name-only HEAD)




FC=gfortran
CC=gcc
FCFLAGS=-c -fPIC -Wunused -O2 -cpp -J$(OBJDIR) -I$(OBJDIR) #-I../include/ uninitialized
ifeq ($(ARCH),Darwin)
	FC=/opt/local/bin/gfortran-mp-4.8
	NCFLAGS=-I/opt/local/include/ 
	NCFLAGS_F2PY=-I/opt/local/include/ 
	LFLAGS= -L$(LIBDIR) -ldfftpack  -L/opt/local/lib/ -llapack
	LDFLAGS=-lnetcdf -lnetcdff  -lz
else
	NCFLAGS :=  $(shell nc-config --fflags)  -O2
	NCFLAGS_F2PY := -I$(shell nc-config --includedir) #f2py does not like -g and -O2
	LFLAGS := -llapack -L$(LIBDIR) -ldfftpack
	LDFLAGS := $(shell nc-config --flibs) -lz
endif




OBJECTS=kinds.o \
        vars_index.o \
	report_module.o \
	settings.o \
	constants.o \
	nan.o \
	zlib_stuff.o \
	mod_fastem4_coef.o \
	gasabs_module.o \
	conversions.o \
	descriptor_file.o \
	vars_atmosphere.o \
	vars_rt.o \
        vars_hydroFullSpec.o \
	mod_io_strings.o \
	getopt.o \
	parse_options.o \
	rt_utilities.o \
	radmat.o \
	convolution.o \
	get_gasabs.o\
	vars_output.o \
	run_rt.o \
	scat_utilities.o \
	mpm93.o \
	eps_water.o \
	get_surface.o \
	mie_scat_utilities.o \
	mie_spheres.o \
	dia2vel.o \
	rescale_spectra.o \
	radar_moments.o \
	radar_spectrum.o \
	radar_simulator.o \
	rosen98_gasabs.o \
	surface.o \
	eps_ice.o \
	eps_mix.o \
	equcom.o \
	land_emis.o \
	equare.o \
	scatdb.o \
	ref_water.o \
	ref_ice.o \
	e_sat_gg_water.o \
	interpolation.o \
	collect_output.o \
	save_active.o \
	fastem4.o \
	specular_surface.o \
	random.o \
	rt4.o \
	radtran4.o \
	radintg4.o \
	radscat4.o \
	drop_size_dist.o \
	make_dist.o \
	make_dist_param.o \
	make_mass_size.o \
	calc_moment.o \
	make_soft_spheroid.o \
	check_print.o \
	tmatrix.o \
	scatProperties.o \
	hydrometeor_extinction.o \
	scatcnv.o \
	tmatrix_lpq.o \
	get_scat_mat.o \
	refractive_index.o \
	dsort.o \
	rho_air.o \
	viscosity_air.o\
	versionNumber.auto.o \
	smooth_savitzky_golay.o \
	radar_hildebrand_sekhon.o \
	write_nc_results.o \
	tmatrix_amplq.lp.o \
	deallocate_everything.o
FOBJECTS=$(addprefix $(OBJDIR),$(OBJECTS))

BIN=pamtra

all: mkdir dfftpack pamtra py py_usStandard

dfftpack: mkdir
	cd tools/dfftpack && $(MAKE)
	cp tools/dfftpack/libdfftpack.a $(LIBDIR)

pamtra: mkdir precompile $(FOBJECTS) $(BINDIR)$(BIN) 


precompile: 
	echo "!edit in makefile only!" > $(SRCDIR)versionNumber.auto.f90
	echo "subroutine versionNumber(gitVersion,gitHash)" >> $(SRCDIR)versionNumber.auto.f90
	echo "implicit none" >> $(SRCDIR)versionNumber.auto.f90
	echo "character(40), intent(out) ::gitVersion,gitHash" >> $(SRCDIR)versionNumber.auto.f90
	echo "gitVersion = '$(gitVersion)'" >> $(SRCDIR)versionNumber.auto.f90
	echo "gitHash = '$(gitHash)'" >> $(SRCDIR)versionNumber.auto.f90
	echo "return" >> $(SRCDIR)versionNumber.auto.f90
	echo "end subroutine versionNumber" >> $(SRCDIR)versionNumber.auto.f90
	$(FC) $(FCFLAGS) $(SRCDIR)versionNumber.auto.f90 -o $(OBJDIR)versionNumber.auto.o #otherwise error on first make run!

mkdir:
	mkdir -p $(OBJDIR)
	mkdir -p $(LIBDIR)
	mkdir -p $(BINDIR)


$(BINDIR)$(BIN): 
	$(FC) -I$(OBJDIR) -o $(BINDIR)$(BIN) $(SRCDIR)pamtra.f90 $(FOBJECTS) $(LFLAGS) $(LDFLAGS) 


$(OBJDIR)scatdb.o:  $(SRCDIR)scatdb.c
	$(CC) -O  -fPIC -c $< -o $@

	
$(OBJDIR)%.o:  $(SRCDIR)%.f90
	$(FC) $(FCFLAGS) $< -o $@

$(OBJDIR)%.o:  $(SRCDIR)%.f
	$(FC) $(FCFLAGS) $< -o $@

$(OBJDIR)write_nc_results.o:  $(SRCDIR)write_nc_results.f90
	$(FC) $(FCFLAGS) $(NCFLAGS) $< -o $@



pamtraDebug: FCFLAGS += -g
pamtraDebug: LFLAGS += -g
pamtraDebug: pamtra
	@echo ""
	@echo "####################################################################################"
	@echo "start debugging with:"
	@echo "gdb ./pamtra"
	@echo "run -n namelist -p profile ..."	
	@echo "####################################################################################"


pamtraProfile: FCFLAGS += -pg
pamtraProfile: LFLAGS += -pg
pamtraProfile: 	pamtra
	@echo ""
	@echo "####################################################################################"
	@echo "analyse gprof output with"
	@echo "gprof ./pamtra | gprof2dot.py | dot -Tpng -o output_old.png"
	@echo "####################################################################################"

pyProfile: NCFLAGS_F2PY += -DF2PY_REPORT_ATEXIT
pyProfile: 	py
	@echo ""
	@echo "####################################################################################"
	@echo "performance report displayed at exit of python"
	@echo "####################################################################################"
pyDebug: NCFLAGS_F2PY += --debug-capi
pyDebug: 	py
	@echo ""
	@echo "####################################################################################"
	@echo "This causes the extension modules to print detailed information while in operation. "
	@echo "####################################################################################"



pyprecompile: 
	@echo "Make backup before deleting old signature file, auto creating can fail."
	@echo "#######################################################################"
	@echo ""
	f2py --overwrite-signature -m pyPamtraLib -h $(SRCDIR)pypamtralib.pyf $(SRCDIR)report_module.f90 $(SRCDIR)deallocate_everything.f90 $(SRCDIR)vars_output.f90 $(SRCDIR)vars_atmosphere.f90 $(SRCDIR)settings.f90 $(SRCDIR)descriptor_file.f90 $(SRCDIR)vars_hydroFullSpec.f90 $(SRCDIR)pyPamtraLib.f90

py: mkdir $(SRCDIR)pyPamtraLib.f90 precompile $(FOBJECTS)
	f2py -I$(OBJDIR) $(NCFLAGS_F2PY) $(LDFLAGS) $(LFLAGS) -c --fcompiler=gnu95  $(SRCDIR)pypamtralib.pyf $(FOBJECTS) $(SRCDIR)pyPamtraLib.f90 
	mv pyPamtraLib.so $(PYTDIR)
	cp $(PYTDIR)/pamtra.py $(BINDIR)

py_usStandard:
	cd tools/py_usStandard/ && $(MAKE) all


pyinstall:
	cp -r pyPamtra ~/lib/python/
	cd tools/py_usStandard/ && $(MAKE) install



clean:
	-rm -f $(OBJDIR)/*.o
	-rm -f $(OBJDIR)/*.mod
	-rm -f $(BINDIR)/*
	cd tools/dfftpack/ && $(MAKE) clean
	cd tools/py_usStandard/ && $(MAKE) clean

htmldoc:
	cd doc && $(MAKE) html
