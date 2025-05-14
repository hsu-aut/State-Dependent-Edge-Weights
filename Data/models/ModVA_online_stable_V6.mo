model ModVA_online_stable
/*
Documentation of Simulation Runs and changes to the model
run 1:        according to documentation to my best knowledge
result run 1: found that 1) B203 is filled much faster that B201 with B202 in the middle
              This will be due to the shorter lenght of the pipes to B203 in comparison to B201
              in reality, however it is the other way around. B201 is filled faster than B203
              This is due to the Tee no receiving as much of the fast moving water
              Thus is not modeled correctly in Modelica. I have adjusted this in reality by slightly closing the vavles above the tanks
              I will try do do something similar for the simulation in run 2.
              Hopefully I can fix this issue by installing automatic valves in the real plant
              Another issue that I found is that P202 pumps much faster than P201 in reality.
              This might be due to differences in pressure drops after the two pumps. I will try to ammend for this in run 2.
  
run 2:       reduced V204.m_flow_nominal and V205.m_flow_nominal, changed N_in for P202
result run 2:
*/
  replaceable package Medium = Modelica.Media.Water.StandardWaterOnePhase constrainedby Modelica.Media.Interfaces.PartialMedium;
  inner Modelica.Fluid.System system(dp_small = 999.9999999999999, energyDynamics = Modelica.Fluid.Types.Dynamics.FixedInitial, massDynamics = Modelica.Fluid.Types.Dynamics.FixedInitial)  annotation(
    Placement(transformation(origin = {-310, 70}, extent = {{-10, -10}, {10, 10}})));
  // Tanks
  Modelica.Fluid.Examples.AST_BatchPlant.BaseClasses.TankWithTopPorts tank_B201(redeclare package Medium = Medium, V0 = 0.0001, crossArea = 0.01431355, height = 0.22, level_start = 0.15108, nPorts = 1, nTopPorts = 1, portsData = {Modelica.Fluid.Vessels.BaseClasses.VesselPortsData(diameter = 0.011, height = 0, zeta_out = 0, zeta_in = 1)}, stiffCharacteristicForEmptyPort = false) annotation(
    Placement(visible = true, transformation(origin = {-89, 31}, extent = {{-11, -11}, {11, 11}}, rotation = 0)));
  Modelica.Fluid.Examples.AST_BatchPlant.BaseClasses.TankWithTopPorts tank_B202(redeclare package Medium = Medium, V0 = 0.0001, crossArea = 0.01431355, height = 0.22, level_start = 0.151, nPorts = 1, nTopPorts = 1, portsData = {Modelica.Fluid.Vessels.BaseClasses.VesselPortsData(diameter = 0.011, height = 0, zeta_out = 0, zeta_in = 1)}, stiffCharacteristicForEmptyPort = false) annotation(
    Placement(visible = true, transformation(origin = {-51, 31}, extent = {{-11, -11}, {11, 11}}, rotation = 0)));
  Modelica.Fluid.Examples.AST_BatchPlant.BaseClasses.TankWithTopPorts tank_B203(redeclare package Medium = Medium, V0 = 0.0001, crossArea = 0.01431355, height = 0.22, level_start = 0.15108, nPorts = 1, nTopPorts = 1, portsData = {Modelica.Fluid.Vessels.BaseClasses.VesselPortsData(diameter = 0.011, height = 0, zeta_out = 0, zeta_in = 1)}, stiffCharacteristicForEmptyPort = false) annotation(
    Placement(visible = true, transformation(origin = {-13, 31}, extent = {{-11, -11}, {11, 11}}, rotation = 0)));
  Modelica.Fluid.Examples.AST_BatchPlant.BaseClasses.TankWithTopPorts tank_B204(redeclare package Medium = Medium, V0 = 0.0001, crossArea = 0.0324, height = 0.35, level_start = 0.00136, nPorts = 1, nTopPorts = 1, portsData = {Modelica.Fluid.Vessels.BaseClasses.VesselPortsData(diameter = 0.011, height = 0, zeta_out = 0, zeta_in = 1)}, stiffCharacteristicForEmptyPort = false) annotation(
    Placement(visible = true, transformation(origin = {47, 25}, extent = {{-11, -11}, {11, 11}}, rotation = 0)));
  /*                       
              Modelica.Fluid.Vessels.OpenTank tank_B201(redeclare package Medium = Medium, T_start = Modelica.Units.Conversions.from_degC(20), crossArea = 0.01431355, height = 0.22, level_start = 0.2, nPorts = 0, portsData = {Modelica.Fluid.Vessels.BaseClasses.VesselPortsData(diameter = 0.01, height = 0.22, zeta_out = 0, zeta_in = 1), Modelica.Fluid.Vessels.BaseClasses.VesselPortsData(diameter = 0.01, height = 0.000001, zeta_out = 0, zeta_in = 1)}, use_portsData = true) annotation(
                Placement(visible = true, transformation(origin = {-88, 28}, extent = {{-12, -12}, {12, 12}}, rotation = 0)));
               
              Modelica.Fluid.Vessels.OpenTank tank_B202(redeclare package Medium = Medium, T_start = Modelica.Units.Conversions.from_degC(20), crossArea = 0.01431355, height = 0.22, level_start = 0.2, nPorts = 0, portsData = {Modelica.Fluid.Vessels.BaseClasses.VesselPortsData(diameter = 0.01, height = 0.22, zeta_out = 0, zeta_in = 1), Modelica.Fluid.Vessels.BaseClasses.VesselPortsData(diameter = 0.01, height = 0.000001, zeta_out = 0, zeta_in = 1)}, use_portsData = true) annotation(
                Placement(visible = true, transformation(origin = {-50, 28}, extent = {{-12, -12}, {12, 12}}, rotation = 0)));
              Modelica.Fluid.Vessels.OpenTank tank_B203(redeclare package Medium = Medium, T_start = Modelica.Units.Conversions.from_degC(20), crossArea = 0.01431355, height = 0.22, level_start = 0.2, nPorts = 0, portsData = {Modelica.Fluid.Vessels.BaseClasses.VesselPortsData(diameter = 0.01, height = 0.22, zeta_out = 0, zeta_in = 1), Modelica.Fluid.Vessels.BaseClasses.VesselPortsData(diameter = 0.01, height = 0.000001, zeta_out = 0, zeta_in = 1)}, use_portsData = true) annotation(
                Placement(visible = true, transformation(origin = {-14, 28}, extent = {{-12, -12}, {12, 12}}, rotation = 0)));
              Modelica.Fluid.Vessels.OpenTank tank_B204(redeclare package Medium = Medium, T_start = Modelica.Units.Conversions.from_degC(20), crossArea = 0.0324, height = 0.35, level_start = 0.01, nPorts = 0, portsData = {Modelica.Fluid.Vessels.BaseClasses.VesselPortsData(diameter = 0.01, height = 0.34, zeta_out = 0, zeta_in = 1), Modelica.Fluid.Vessels.BaseClasses.VesselPortsData(diameter = 0.01, height = 0.000001, zeta_out = 0, zeta_in = 1)}, use_portsData = true) annotation(
                Placement(visible = true, transformation(origin = {46, 26}, extent = {{-14, -14}, {14, 14}}, rotation = 0)));
            */
  //Actuators
  //Valves
  Modelica.Fluid.Valves.ValveLinear V201(redeclare package Medium = Medium, dp_nominal = 20, dp_start = 0, m_flow_nominal = 0.1, m_flow_small = 0.000001, m_flow_start = 0) annotation(
    Placement(visible = true, transformation(origin = {-88, -12}, extent = {{6, -6}, {-6, 6}}, rotation = 90)));
  Modelica.Fluid.Valves.ValveLinear V202(redeclare package Medium = Medium, dp_nominal = 20, dp_start = 0, m_flow_nominal = 0.1, m_flow_small = 0.000001, m_flow_start = 0) annotation(
    Placement(visible = true, transformation(origin = {-50, -10}, extent = {{6, -6}, {-6, 6}}, rotation = 90)));
  Modelica.Fluid.Valves.ValveLinear V203(redeclare package Medium = Medium, dp_nominal = 20, dp_start = 0, m_flow_nominal = 0.1, m_flow_small = 0.000001, m_flow_start = 0) annotation(
    Placement(transformation(origin = {-14, -8}, extent = {{6, -6}, {-6, 6}}, rotation = 90)));
  Modelica.Fluid.Valves.ValveLinear V204(redeclare package Medium = Medium, dp_nominal = 20, dp_start = 0, m_flow_nominal = 0.1, m_flow_small = 0.000001, m_flow_start = 0) annotation(
    Placement(transformation(origin = {-88, 70}, extent = {{6, -6}, {-6, 6}}, rotation = 90)));
  Modelica.Fluid.Valves.ValveLinear V205(redeclare package Medium = Medium, dp_nominal = 20, dp_start = 0, m_flow_nominal = 0.1, m_flow_small = 0.000001, m_flow_start = 0) annotation(
    Placement(transformation(origin = {-50, 68}, extent = {{6, -6}, {-6, 6}}, rotation = 90)));
  Modelica.Fluid.Valves.ValveLinear V206(redeclare package Medium = Medium, dp_nominal = 20, dp_start = 0, m_flow_nominal = 0.1, m_flow_small = 0.000001, m_flow_start = 0) annotation(
    Placement(transformation(origin = {-14, 66}, extent = {{6, -6}, {-6, 6}}, rotation = 90)));
  Modelica.Fluid.Valves.ValveLinear V207(redeclare package Medium = Medium, dp_nominal = 2000, dp_start = 0, m_flow_nominal = 0.1, m_flow_small = 0.000001, m_flow_start = 0) annotation(
    Placement(visible = true, transformation(origin = {88, 28}, extent = {{6, 6}, {-6, -6}}, rotation = -90)));
  Modelica.Fluid.Valves.ValveLinear V209(redeclare package Medium = Medium, dp_nominal = 20, dp_start = 0, m_flow_nominal = 0.1, m_flow_small = 0.000001, m_flow_start = 0) annotation(
    Placement(visible = true, transformation(origin = {120, -10}, extent = {{-6, -6}, {6, 6}}, rotation = 0)));
  //Pumps
  Modelica.Fluid.Machines.PrescribedPump P201(redeclare package Medium = Medium, N_nominal = 155, m_flow_start = 0.000001, T_start = system.T_start, V(displayUnit = "m3") = 0.00004398128, checkValve = true, checkValveHomotopy = Modelica.Fluid.Types.CheckValveHomotopyType.Closed, energyDynamics = Modelica.Fluid.Types.Dynamics.FixedInitial, redeclare function flowCharacteristic = Modelica.Fluid.Machines.BaseClasses.PumpCharacteristics.quadraticFlow(V_flow_nominal = {0.000122, 0.0002, 0.00025}, head_nominal = {2.045, 1.534, 1.022}), massDynamics = Modelica.Fluid.Types.Dynamics.FixedInitial, nParallel = 1, p_a_start = 100000, p_b_start = 100000, use_N_in = true) annotation(
    Placement(visible = true, transformation(origin = {-9, -55}, extent = {{-7, -7}, {7, 7}}, rotation = 0)));
  Modelica.Fluid.Machines.PrescribedPump P202(redeclare package Medium = Medium, N_nominal = 166.43, m_flow_start = 0.000001, T_start = system.T_start, V(displayUnit = "m3") = 0.00004398128, checkValve = true, checkValveHomotopy = Modelica.Fluid.Types.CheckValveHomotopyType.Closed, energyDynamics = Modelica.Fluid.Types.Dynamics.FixedInitial, redeclare function flowCharacteristic = Modelica.Fluid.Machines.BaseClasses.PumpCharacteristics.quadraticFlow(V_flow_nominal = {0.000122, 0.0002, 0.00025}, head_nominal = {2.045, 1.534, 1.022}), massDynamics = Modelica.Fluid.Types.Dynamics.FixedInitial, nParallel = 1, p_a_start = 100000, p_b_start = 100000, use_N_in = true) annotation(
    Placement(transformation(origin = {65, -19}, extent = {{-7, -7}, {7, 7}})));
  //Sensors
  Modelica.Fluid.Sensors.VolumeFlowRate FI201(redeclare package Medium = Medium) annotation(
    Placement(transformation(origin = {12, -26}, extent = {{-6, 6}, {6, -6}}, rotation = 90)));
  //Pipes
  Modelica.Fluid.Pipes.StaticPipe pipe_V206_B201(redeclare package Medium = Medium, diameter = 0.01, height_ab = -0.05, length = 0.15) annotation(
    Placement(transformation(origin = {-88, 51}, extent = {{5, -5}, {-5, 5}}, rotation = 90)));
  Modelica.Fluid.Pipes.StaticPipe pipe_V205_B202(redeclare package Medium = Medium, diameter = 0.01, height_ab = -0.05, length = 0.15) annotation(
    Placement(transformation(origin = {-50, 51}, extent = {{5, -5}, {-5, 5}}, rotation = 90)));
  Modelica.Fluid.Pipes.StaticPipe pipe_V204_B203(redeclare package Medium = Medium, diameter = 0.01, height_ab = -0.05, length = 0.15) annotation(
    Placement(transformation(origin = {-14, 51}, extent = {{5, -5}, {-5, 5}}, rotation = 90)));
  Modelica.Fluid.Pipes.StaticPipe pipe_B201_V201(redeclare package Medium = Medium, diameter = 0.01, height_ab = -0.04, length = 0.27) annotation(
    Placement(visible = true, transformation(origin = {-88, 5}, extent = {{5, -5}, {-5, 5}}, rotation = 90)));
  Modelica.Fluid.Pipes.StaticPipe pipe_B202_V202(redeclare package Medium = Medium, diameter = 0.01, height_ab = -0.04, length = 0.27) annotation(
    Placement(visible = true, transformation(origin = {-50, 5}, extent = {{5, -5}, {-5, 5}}, rotation = 90)));
  Modelica.Fluid.Pipes.StaticPipe pipe_B203_V203(redeclare package Medium = Medium, diameter = 0.01, height_ab = -0.04, length = 0.27) annotation(
    Placement(transformation(origin = {-14, 5}, extent = {{5, -5}, {-5, 5}}, rotation = 90)));
  Modelica.Fluid.Pipes.StaticPipe pipe_V201_Tee1(redeclare package Medium = Medium, diameter = 0.01, height_ab = 0, length = 0.19) annotation(
    Placement(visible = true, transformation(origin = {-76, -36}, extent = {{-6, -6}, {6, 6}}, rotation = 0)));
  Modelica.Fluid.Pipes.StaticPipe pipe_V202_Tee2(redeclare package Medium = Medium, diameter = 0.01, height_ab = 0, length = 0.11) annotation(
    Placement(visible = true, transformation(origin = {-43, -19}, extent = {{-5, -5}, {5, 5}}, rotation = 0)));
  Modelica.Fluid.Pipes.StaticPipe pipe_V203_Tee2(redeclare package Medium = Medium, diameter = 0.01, height_ab = 0, length = 0.31) annotation(
    Placement(visible = true, transformation(origin = {-19, -19}, extent = {{5, -5}, {-5, 5}}, rotation = 0)));
  Modelica.Fluid.Pipes.StaticPipe pipe_Tee2_Tee1(redeclare package Medium = Medium, diameter = 0.01, height_ab = 0, length = 0.11) annotation(
    Placement(visible = true, transformation(origin = {-47, -29}, extent = {{5, -5}, {-5, 5}}, rotation = 0)));
  Modelica.Fluid.Pipes.StaticPipe pipe_Tee1_P201(redeclare package Medium = Medium, diameter = 0.01, height_ab = 0, length = 0.16) annotation(
    Placement(visible = true, transformation(origin = {-37, -55}, extent = {{-5, -5}, {5, 5}}, rotation = 0)));
  Modelica.Fluid.Pipes.StaticPipe pipe_P201_FI201(redeclare package Medium = Medium, diameter = 0.01, height_ab = 0.05, length = 0.05) annotation(
    Placement(visible = true, transformation(origin = {13, -45}, extent = {{-5, -5}, {5, 5}}, rotation = 90)));
  Modelica.Fluid.Pipes.StaticPipe pipe_FI201_B204(redeclare package Medium = Medium, diameter = 0.01, height_ab = 0.405, length = 0.57) annotation(
    Placement(visible = true, transformation(origin = {13, -5}, extent = {{-5, -5}, {5, 5}}, rotation = 90)));
  Modelica.Fluid.Pipes.StaticPipe pipe_B204_P202(redeclare package Medium = Medium, diameter = 0.01, height_ab = -0.055, length = 0.65) annotation(
    Placement(visible = true, transformation(origin = {47, -7}, extent = {{5, 5}, {-5, -5}}, rotation = 90)));
  Modelica.Fluid.Pipes.StaticPipe pipe_P202_Tee3(redeclare package Medium = Medium, diameter = 0.01, height_ab = 0.1, length = 0.1) annotation(
    Placement(transformation(origin = {81, -19}, extent = {{-5, 5}, {5, -5}})));
  Modelica.Fluid.Pipes.StaticPipe pipe_Tee3_V207(redeclare package Medium = Medium, diameter = 0.01, height_ab = 0.09, length = 0.09) annotation(
    Placement(visible = true, transformation(origin = {101, -9}, extent = {{-5, 5}, {5, -5}}, rotation = 0)));
  Modelica.Fluid.Pipes.StaticPipe pipe_Tee3_V209(redeclare package Medium = Medium, diameter = 0.01, height_ab = 0, length = 0.12) annotation(
    Placement(visible = true, transformation(origin = {87, 7}, extent = {{-5, 5}, {5, -5}}, rotation = 90)));
  Modelica.Fluid.Pipes.StaticPipe pipe_V207_Tee4(redeclare package Medium = Medium, diameter = 0.01, height_ab = 0.215, length = 0.44) annotation(
    Placement(visible = true, transformation(origin = {87, 49}, extent = {{-5, 5}, {5, -5}}, rotation = 90)));
  Modelica.Fluid.Pipes.StaticPipe pipe_Tee4_V204(redeclare package Medium = Medium, diameter = 0.01, height_ab = 0, length = 0.1) annotation(
    Placement(visible = true, transformation(origin = {-15, 85}, extent = {{5, -5}, {-5, 5}}, rotation = 90)));
  Modelica.Fluid.Pipes.StaticPipe pipe_Tee4_Tee5(redeclare package Medium = Medium, diameter = 0.01, height_ab = 0, length = 0.2) annotation(
    Placement(visible = true, transformation(origin = {-31, 99}, extent = {{5, 5}, {-5, -5}}, rotation = 0)));
  Modelica.Fluid.Pipes.StaticPipe pipe_Tee5_V205(redeclare package Medium = Medium, diameter = 0.01, height_ab = 0, length = 0.10) annotation(
    Placement(visible = true, transformation(origin = {-49, 85}, extent = {{5, 5}, {-5, -5}}, rotation = 90)));
  Modelica.Fluid.Pipes.StaticPipe pipe_Tee5_V206(redeclare package Medium = Medium, diameter = 0.01, height_ab = 0, length = 0.30) annotation(
    Placement(visible = true, transformation(origin = {-69, 99}, extent = {{5, 5}, {-5, -5}}, rotation = 0)));
  // Fittings
  //Tees
  Modelica.Fluid.Fittings.TeeJunctionVolume Tee1(redeclare package Medium = Medium, V = 0.0000003) annotation(
    Placement(visible = true, transformation(origin = {-59, -45}, extent = {{5, -5}, {-5, 5}}, rotation = 90)));
  Modelica.Fluid.Fittings.TeeJunctionVolume Tee3(redeclare package Medium = Medium, V = 0.0000003) annotation(
    Placement(visible = true, transformation(origin = {87, -9}, extent = {{-5, 5}, {5, -5}}, rotation = 90)));
  Modelica.Fluid.Fittings.TeeJunctionVolume Tee2(redeclare package Medium = Medium, V = 0.0000003) annotation(
    Placement(visible = true, transformation(origin = {-31, -23}, extent = {{-5, -5}, {5, 5}}, rotation = -90)));
  Modelica.Fluid.Fittings.TeeJunctionVolume Tee4(redeclare package Medium = Medium, V = 0.0000003) annotation(
    Placement(visible = true, transformation(origin = {-15, 99}, extent = {{5, 5}, {-5, -5}}, rotation = 0)));
  Modelica.Fluid.Fittings.TeeJunctionVolume Tee5(redeclare package Medium = Medium, V = 0.0000003) annotation(
    Placement(visible = true, transformation(origin = {-49, 99}, extent = {{5, 5}, {-5, -5}}, rotation = 0)));
  //Boundaries
  Modelica.Fluid.Sources.FixedBoundary boundary(redeclare package Medium = Medium, nPorts = 1) annotation(
    Placement(visible = true, transformation(origin = {142, -18}, extent = {{10, -10}, {-10, 10}}, rotation = 0)));
  //Signals
  //Pump Characteristics
  //Control
  //State Graph
  // Cut to reduce compilation time
  /*
                  Modelica.Blocks.Sources.RealExpression B201_level(y = tank_B201.level) annotation(
                    Placement(visible = true, transformation(origin = {-376, 34}, extent = {{-10, -10}, {10, 10}}, rotation = 0)));
                  Modelica.Blocks.Sources.RealExpression B202_level(y = tank_B202.level) annotation(
                    Placement(visible = true, transformation(origin = {-378, -2}, extent = {{-10, -10}, {10, 10}}, rotation = 0)));
                  Modelica.Blocks.Sources.RealExpression B203_level(y = tank_B203.level) annotation(
                    Placement(visible = true, transformation(origin = {-378, -48}, extent = {{-10, -10}, {10, 10}}, rotation = 0)));
                  Modelica.Blocks.Sources.RealExpression B204_level(y = tank_B204.level) annotation(
                    Placement(visible = true, transformation(origin = {-378, -96}, extent = {{-10, -10}, {10, 10}}, rotation = 0)));
                  Modelica.Blocks.Sources.BooleanExpression LA210(y = if tank_B201.level > 0.219 then true else false) annotation(
                    Placement(visible = true, transformation(origin = {-350, 42}, extent = {{-10, -10}, {10, 10}}, rotation = 0)));
                  Modelica.Blocks.Sources.BooleanExpression LS202(y = if tank_B201.level < 0.01 then true else false) annotation(
                    Placement(visible = true, transformation(origin = {-350, 28}, extent = {{-10, -10}, {10, 10}}, rotation = 0)));
                  Modelica.Blocks.Sources.BooleanExpression LA211(y = if tank_B202.level > 0.219 then true else false) annotation(
                    Placement(visible = true, transformation(origin = {-350, 6}, extent = {{-10, -10}, {10, 10}}, rotation = 0)));
                  Modelica.Blocks.Sources.BooleanExpression LS203(y = if tank_B202.level < 0.01 then true else false) annotation(
                    Placement(visible = true, transformation(origin = {-350, -10}, extent = {{-10, -10}, {10, 10}}, rotation = 0)));
                  Modelica.Blocks.Sources.BooleanExpression LA212(y = if tank_B203.level > 0.219 then true else false) annotation(
                    Placement(visible = true, transformation(origin = {-350, -42}, extent = {{-10, -10}, {10, 10}}, rotation = 0)));
                  Modelica.Blocks.Sources.BooleanExpression LS204(y = if tank_B203.level < 0.01 then true else false) annotation(
                    Placement(visible = true, transformation(origin = {-350, -56}, extent = {{-10, -10}, {10, 10}}, rotation = 0)));
                  Modelica.Blocks.Sources.BooleanExpression LA213(y = if tank_B204.level > 0.349 then true else false) annotation(
                    Placement(visible = true, transformation(origin = {-350, -80}, extent = {{-10, -10}, {10, 10}}, rotation = 0)));
                  Modelica.Blocks.Sources.BooleanExpression LS205(y = if tank_B204.level > 0.175 then true else false) annotation(
                    Placement(visible = true, transformation(origin = {-350, -96}, extent = {{-10, -10}, {10, 10}}, rotation = 0)));
                  Modelica.Blocks.Sources.BooleanExpression LS206(y = if tank_B204.level < 0.01 then true else false) annotation(
                    Placement(visible = true, transformation(origin = {-350, -110}, extent = {{-10, -10}, {10, 10}}, rotation = 0)));
                 */
  Modelica.Blocks.Continuous.FirstOrder P201_Characteristic(T = 1, k = 100) annotation(
    Placement(visible = true, transformation(origin = {-90, -70}, extent = {{-10, -10}, {10, 10}}, rotation = 0)));
  Modelica.Blocks.Continuous.FirstOrder P202_Characteristic(T = 1, k = 100) annotation(
    Placement(visible = true, transformation(origin = {46, -70}, extent = {{-10, -10}, {10, 10}}, rotation = 0)));
  Modelica.Blocks.Sources.CombiTimeTable ActuatorControl(table = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0; 0.67, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0; 9.81, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0; 36.58, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0; 61.01, 0.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0; 63.44, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0; 87.57, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0; 90.04, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0; 117.75, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0; 145.55, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 1.0; 172.38, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0; 173.98, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0; 199.04, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0; 226.02, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0; 251.66, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0; 278.88, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0; 305.97, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 1.0; 335.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0; 337.13, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0; 361.86, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0; 388.63, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0; 414.92, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0; 442.35, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0; 470.99, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 1.0; 499.9, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0; 527.47, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0; 553.48, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0; 578.81, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0; 580.65, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0; 599.80, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], timeEvents = Modelica.Blocks.Types.TimeEvents.NoTimeEvents)  annotation(
    Placement(transformation(origin = {-310, -40}, extent = {{-10, -10}, {10, 10}})));
  Modelica.Blocks.Math.RealToBoolean R2B_P202(threshold = 0.98) annotation(
    Placement(transformation(origin = {-226, -126}, extent = {{-6, -6}, {6, 6}})));
  Modelica.Blocks.Logical.RSFlipFlop FlipFlop_P202 annotation(
    Placement(transformation(origin = {-176, -138}, extent = {{-6, -6}, {6, 6}})));
  Modelica.Blocks.Math.BooleanToReal B2R_P202 annotation(
    Placement(transformation(origin = {-146, -134}, extent = {{-6, -6}, {6, 6}})));
  Modelica.Blocks.Logical.Not Not_P202 annotation(
    Placement(transformation(origin = {-204, -142}, extent = {{-4, -4}, {4, 4}})));
  Modelica.Blocks.Math.RealToBoolean R2B_2_P202(threshold = 0.01) annotation(
    Placement(transformation(origin = {-226, -142}, extent = {{-6, -6}, {6, 6}})));
  Modelica.Blocks.Math.RealToBoolean R2B_P201(threshold = 0.98) annotation(
    Placement(transformation(origin = {-226, -94}, extent = {{-6, -6}, {6, 6}})));
  Modelica.Blocks.Logical.RSFlipFlop FlipFlop_P201 annotation(
    Placement(transformation(origin = {-176, -106}, extent = {{-6, -6}, {6, 6}})));
  Modelica.Blocks.Math.BooleanToReal B2R_P201 annotation(
    Placement(transformation(origin = {-146, -102}, extent = {{-6, -6}, {6, 6}})));
  Modelica.Blocks.Logical.Not Not_P201 annotation(
    Placement(transformation(origin = {-204, -110}, extent = {{-4, -4}, {4, 4}})));
  Modelica.Blocks.Math.RealToBoolean R2B_2_P201(threshold = 0.01) annotation(
    Placement(transformation(origin = {-226, -110}, extent = {{-6, -6}, {6, 6}})));
  Modelica.Blocks.Math.RealToBoolean R2B_V206(threshold = 0.98) annotation(
    Placement(transformation(origin = {-226, -62}, extent = {{-6, -6}, {6, 6}})));
  Modelica.Blocks.Logical.RSFlipFlop FlipFlop_V206 annotation(
    Placement(transformation(origin = {-176, -74}, extent = {{-6, -6}, {6, 6}})));
  Modelica.Blocks.Math.BooleanToReal B2R_V206 annotation(
    Placement(transformation(origin = {-146, -70}, extent = {{-6, -6}, {6, 6}})));
  Modelica.Blocks.Logical.Not Not_V206 annotation(
    Placement(transformation(origin = {-204, -78}, extent = {{-4, -4}, {4, 4}})));
  Modelica.Blocks.Math.RealToBoolean R2B_2_V206(threshold = 0.01) annotation(
    Placement(transformation(origin = {-226, -78}, extent = {{-6, -6}, {6, 6}})));
  Modelica.Blocks.Math.RealToBoolean R2B_V205(threshold = 0.98) annotation(
    Placement(transformation(origin = {-226, -30}, extent = {{-6, -6}, {6, 6}})));
  Modelica.Blocks.Logical.RSFlipFlop FlipFlop_V205 annotation(
    Placement(transformation(origin = {-176, -42}, extent = {{-6, -6}, {6, 6}})));
  Modelica.Blocks.Math.BooleanToReal B2R_V205 annotation(
    Placement(transformation(origin = {-146, -38}, extent = {{-6, -6}, {6, 6}})));
  Modelica.Blocks.Logical.Not Not_V205 annotation(
    Placement(transformation(origin = {-204, -46}, extent = {{-4, -4}, {4, 4}})));
  Modelica.Blocks.Math.RealToBoolean R2B_2_V205(threshold = 0.01) annotation(
    Placement(transformation(origin = {-226, -46}, extent = {{-6, -6}, {6, 6}})));
  Modelica.Blocks.Math.RealToBoolean R2B_V204(threshold = 0.98) annotation(
    Placement(transformation(origin = {-226, 2}, extent = {{-6, -6}, {6, 6}})));
  Modelica.Blocks.Logical.RSFlipFlop FlipFlop_V204 annotation(
    Placement(transformation(origin = {-176, -10}, extent = {{-6, -6}, {6, 6}})));
  Modelica.Blocks.Math.BooleanToReal B2R_V204 annotation(
    Placement(transformation(origin = {-146, -6}, extent = {{-6, -6}, {6, 6}})));
  Modelica.Blocks.Logical.Not Not_V204 annotation(
    Placement(transformation(origin = {-204, -14}, extent = {{-4, -4}, {4, 4}})));
  Modelica.Blocks.Math.RealToBoolean R2B_2_V204(threshold = 0.01) annotation(
    Placement(transformation(origin = {-226, -14}, extent = {{-6, -6}, {6, 6}})));
  Modelica.Blocks.Math.RealToBoolean R2B_V203(threshold = 0.98) annotation(
    Placement(transformation(origin = {-226, 34}, extent = {{-6, -6}, {6, 6}})));
  Modelica.Blocks.Logical.RSFlipFlop FlipFlop_V203 annotation(
    Placement(transformation(origin = {-176, 22}, extent = {{-6, -6}, {6, 6}})));
  Modelica.Blocks.Math.BooleanToReal B2R_V203 annotation(
    Placement(transformation(origin = {-146, 26}, extent = {{-6, -6}, {6, 6}})));
  Modelica.Blocks.Logical.Not Not_V203 annotation(
    Placement(transformation(origin = {-204, 18}, extent = {{-4, -4}, {4, 4}})));
  Modelica.Blocks.Math.RealToBoolean R2B_2_V203(threshold = 0.01) annotation(
    Placement(transformation(origin = {-226, 18}, extent = {{-6, -6}, {6, 6}})));
  Modelica.Blocks.Math.RealToBoolean R2B_V209(threshold = 0.98) annotation(
    Placement(transformation(origin = {-226, -158}, extent = {{-6, -6}, {6, 6}})));
  Modelica.Blocks.Logical.RSFlipFlop FlipFlop_V209 annotation(
    Placement(transformation(origin = {-176, -170}, extent = {{-6, -6}, {6, 6}})));
  Modelica.Blocks.Math.BooleanToReal B2R_V209 annotation(
    Placement(transformation(origin = {-146, -166}, extent = {{-6, -6}, {6, 6}})));
  Modelica.Blocks.Logical.Not Not_V209 annotation(
    Placement(transformation(origin = {-204, -174}, extent = {{-4, -4}, {4, 4}})));
  Modelica.Blocks.Math.RealToBoolean R2B_2_V209(threshold = 0.01) annotation(
    Placement(transformation(origin = {-226, -174}, extent = {{-6, -6}, {6, 6}})));
  Modelica.Blocks.Math.RealToBoolean R2B_V202(threshold = 0.98) annotation(
    Placement(transformation(origin = {-226, 66}, extent = {{-6, -6}, {6, 6}})));
  Modelica.Blocks.Logical.RSFlipFlop FlipFlop_V202 annotation(
    Placement(transformation(origin = {-176, 54}, extent = {{-6, -6}, {6, 6}})));
  Modelica.Blocks.Math.BooleanToReal B2R_V202 annotation(
    Placement(transformation(origin = {-146, 58}, extent = {{-6, -6}, {6, 6}})));
  Modelica.Blocks.Logical.Not Not_V202 annotation(
    Placement(transformation(origin = {-204, 50}, extent = {{-4, -4}, {4, 4}})));
  Modelica.Blocks.Math.RealToBoolean R2B_2_V202(threshold = 0.01) annotation(
    Placement(transformation(origin = {-226, 50}, extent = {{-6, -6}, {6, 6}})));
  Modelica.Blocks.Math.RealToBoolean R2B_V201(threshold = 0.98) annotation(
    Placement(transformation(origin = {-226, 98}, extent = {{-6, -6}, {6, 6}})));
  Modelica.Blocks.Logical.RSFlipFlop FlipFlop_V201 annotation(
    Placement(transformation(origin = {-176, 86}, extent = {{-6, -6}, {6, 6}})));
  Modelica.Blocks.Math.BooleanToReal B2R_V201 annotation(
    Placement(transformation(origin = {-146, 90}, extent = {{-6, -6}, {6, 6}})));
  Modelica.Blocks.Logical.Not Not_V201 annotation(
    Placement(transformation(origin = {-204, 82}, extent = {{-4, -4}, {4, 4}})));
  Modelica.Blocks.Math.RealToBoolean R2B_2_V201(threshold = 0.01) annotation(
    Placement(transformation(origin = {-226, 82}, extent = {{-6, -6}, {6, 6}})));
equation
//Control_V201.y = if time < 5 then true else false;
  V207.opening = 1;
//V209.opening = 0.00000001;
/*
  B204_empty.condition = if tank_B201.level > 0.219 or tank_B202.level > 0.219 or tank_B203.level > 0.219 or tank_B204.level < 0.01 then true else false;
  V201.opening = if Empty_B201.active then 1 else 0;
  V202.opening = if Empty_B202.active then 1 else 0;
  V203.opening = if Empty_B203.active then 1 else 0;
  V204.opening = if Empty_B204.active then 1 else 0;
  V205.opening = if Empty_B204.active then 1 else 0;
  V206.opening = if Empty_B204.active then 1 else 0;
  V207.opening = if Empty_B204.active then 1 else 0;
  V209.opening = 0;
  P201.N_in = if Empty_B201.active or Empty_B202.active or Empty_B203.active then 166.43 else 0.0000001;
  P202.N_in = if Empty_B204.active then 166.43 else 0.0000001;
  */
  connect(P201.port_b, pipe_P201_FI201.port_a) annotation(
    Line(points = {{-2, -54}, {14, -54}, {14, -50}}, color = {0, 127, 255}));
  connect(pipe_P201_FI201.port_b, FI201.port_a) annotation(
    Line(points = {{14, -40}, {14, -36}, {12, -36}, {12, -32}}, color = {0, 127, 255}));
  connect(FI201.port_b, pipe_FI201_B204.port_a) annotation(
    Line(points = {{12, -20}, {12, -15}, {14, -15}, {14, -10}}, color = {0, 127, 255}));
  connect(pipe_B204_P202.port_b, P202.port_a) annotation(
    Line(points = {{47, -12}, {47, -19}, {58, -19}}, color = {0, 127, 255}));
  connect(pipe_P202_Tee3.port_a, P202.port_b) annotation(
    Line(points = {{76, -19}, {72, -19}}, color = {0, 127, 255}));
  connect(pipe_V202_Tee2.port_b, Tee2.port_1) annotation(
    Line(points = {{-38, -18}, {-30, -18}}, color = {0, 127, 255}));
  connect(pipe_V203_Tee2.port_b, Tee2.port_3) annotation(
    Line(points = {{-24, -19}, {-26, -18}, {-26, -22}}, color = {0, 127, 255}));
  connect(Tee2.port_2, pipe_Tee2_Tee1.port_a) annotation(
    Line(points = {{-30, -28}, {-42, -28}}, color = {0, 127, 255}));
  connect(pipe_V201_Tee1.port_b, Tee1.port_3) annotation(
    Line(points = {{-70, -36}, {-64, -36}, {-64, -44}}, color = {0, 127, 255}));
  connect(Tee1.port_1, pipe_Tee2_Tee1.port_b) annotation(
    Line(points = {{-58, -40}, {-58, -28}, {-52, -28}}, color = {0, 127, 255}));
  connect(Tee1.port_2, pipe_Tee1_P201.port_a) annotation(
    Line(points = {{-58, -50}, {-60, -50}, {-60, -54}, {-42, -54}}, color = {0, 127, 255}));
  connect(pipe_Tee1_P201.port_b, P201.port_a) annotation(
    Line(points = {{-32, -54}, {-16, -54}}, color = {0, 127, 255}));
  connect(pipe_P202_Tee3.port_b, Tee3.port_1) annotation(
    Line(points = {{86, -19}, {88, -19}, {88, -14}}, color = {0, 127, 255}));
  connect(Tee3.port_3, pipe_Tee3_V207.port_a) annotation(
    Line(points = {{92, -8}, {96, -8}}, color = {0, 127, 255}));
  connect(Tee3.port_2, pipe_Tee3_V209.port_a) annotation(
    Line(points = {{88, -4}, {88, 2}}, color = {0, 127, 255}));
  connect(pipe_Tee5_V206.port_a, Tee5.port_2) annotation(
    Line(points = {{-64, 100}, {-54, 100}}, color = {0, 127, 255}));
  connect(Tee5.port_3, pipe_Tee5_V205.port_a) annotation(
    Line(points = {{-48, 94}, {-48, 90}}));
  connect(Tee5.port_1, pipe_Tee4_Tee5.port_b) annotation(
    Line(points = {{-44, 100}, {-36, 100}}, color = {0, 127, 255}));
  connect(pipe_Tee4_Tee5.port_a, Tee4.port_2) annotation(
    Line(points = {{-26, 100}, {-20, 100}}, color = {0, 127, 255}));
  connect(Tee4.port_3, pipe_Tee4_V204.port_a) annotation(
    Line(points = {{-14, 94}, {-14, 90}}, color = {0, 127, 255}));
  connect(Tee4.port_1, pipe_V207_Tee4.port_b) annotation(
    Line(points = {{-10, 100}, {88, 100}, {88, 54}}, color = {0, 127, 255}));
  connect(pipe_V206_B201.port_b, tank_B201.topPorts[1]) annotation(
    Line(points = {{-88, 46}, {-88, 42}}, color = {0, 127, 255}));
  connect(tank_B201.ports[1], pipe_B201_V201.port_a) annotation(
    Line(points = {{-88, 20}, {-88, 10}}, color = {0, 127, 255}));
  connect(pipe_V205_B202.port_b, tank_B202.topPorts[1]) annotation(
    Line(points = {{-50, 46}, {-50, 42}}, color = {0, 127, 255}));
  connect(tank_B202.ports[1], pipe_B202_V202.port_a) annotation(
    Line(points = {{-50, 20}, {-50, 10}}, color = {0, 127, 255}));
  connect(tank_B203.topPorts[1], pipe_V204_B203.port_b) annotation(
    Line(points = {{-12, 42}, {-14, 42}, {-14, 46}}, color = {0, 127, 255}));
  connect(tank_B203.ports[1], pipe_B203_V203.port_a) annotation(
    Line(points = {{-12, 20}, {-14, 20}, {-14, 10}}, color = {0, 127, 255}));
  connect(tank_B204.ports[1], pipe_B204_P202.port_a) annotation(
    Line(points = {{48, 14}, {48, -2}}, color = {0, 127, 255}));
  connect(pipe_FI201_B204.port_b, tank_B204.topPorts[1]) annotation(
    Line(points = {{14, 0}, {10, 0}, {10, 46}, {48, 46}, {48, 36}}, color = {0, 127, 255}));
  connect(V207.port_b, pipe_V207_Tee4.port_a) annotation(
    Line(points = {{88, 34}, {88, 44}}, color = {0, 127, 255}));
  connect(V207.port_a, pipe_Tee3_V209.port_b) annotation(
    Line(points = {{88, 22}, {88, 12}}, color = {0, 127, 255}));
  connect(V209.port_a, pipe_Tee3_V207.port_b) annotation(
    Line(points = {{114, -10}, {106, -10}, {106, -8}}));
  connect(V209.port_b, boundary.ports[1]) annotation(
    Line(points = {{126, -10}, {132, -10}, {132, -18}}, color = {0, 127, 255}));
  connect(V201.port_a, pipe_B201_V201.port_b) annotation(
    Line(points = {{-88, -6}, {-88, 0}}, color = {0, 127, 255}));
  connect(V201.port_b, pipe_V201_Tee1.port_a) annotation(
    Line(points = {{-88, -18}, {-88, -36}, {-82, -36}}, color = {0, 127, 255}));
  connect(V202.port_a, pipe_B202_V202.port_b) annotation(
    Line(points = {{-50, -4}, {-50, 0}}, color = {0, 127, 255}));
  connect(V202.port_b, pipe_V202_Tee2.port_a) annotation(
    Line(points = {{-50, -16}, {-50, -18}, {-48, -18}}, color = {0, 127, 255}));
  connect(V203.port_a, pipe_B203_V203.port_b) annotation(
    Line(points = {{-14, -2}, {-14, 0}}, color = {0, 127, 255}));
  connect(V203.port_b, pipe_V203_Tee2.port_a) annotation(
    Line(points = {{-14, -14}, {-14, -18}}, color = {0, 127, 255}));
  connect(P201_Characteristic.y, P201.N_in) annotation(
    Line(points = {{-78, -70}, {-78, -59}, {-44, -59}, {-44, -60}, {-25.5, -60}, {-25.5, -48}, {-9, -48}}, color = {0, 0, 127}));
  connect(P202_Characteristic.y, P202.N_in) annotation(
    Line(points = {{58, -70}, {58, -12}, {65, -12}}, color = {0, 0, 127}));
  connect(V205.port_a, pipe_Tee5_V205.port_b) annotation(
    Line(points = {{-50, 74}, {-50, 78}, {-48, 78}, {-48, 80}}, color = {0, 127, 255}));
  connect(V205.port_b, pipe_V205_B202.port_a) annotation(
    Line(points = {{-50, 62}, {-50, 56}}, color = {0, 127, 255}));
  connect(pipe_Tee4_V204.port_b, V206.port_a) annotation(
    Line(points = {{-14, 80}, {-14, 72}}, color = {0, 127, 255}));
  connect(V206.port_b, pipe_V204_B203.port_a) annotation(
    Line(points = {{-14, 60}, {-14, 56}}, color = {0, 127, 255}));
  connect(pipe_Tee5_V206.port_b, V204.port_a) annotation(
    Line(points = {{-74, 100}, {-88, 100}, {-88, 76}}, color = {0, 127, 255}));
  connect(FlipFlop_P202.Q, B2R_P202.u) annotation(
    Line(points = {{-169.4, -134.4}, {-153.4, -134.4}}, color = {255, 0, 255}));
  connect(Not_P202.y, FlipFlop_P202.R) annotation(
    Line(points = {{-199.6, -142}, {-182.6, -142}}, color = {255, 0, 255}));
  connect(R2B_P202.y, FlipFlop_P202.S) annotation(
    Line(points = {{-219.4, -126}, {-191.2, -126}, {-191.2, -134}, {-183, -134}}, color = {255, 0, 255}));
  connect(R2B_2_P202.y, Not_P202.u) annotation(
    Line(points = {{-219.4, -142}, {-209, -142}}, color = {255, 0, 255}));
  connect(FlipFlop_P201.Q, B2R_P201.u) annotation(
    Line(points = {{-169.4, -102.4}, {-153.4, -102.4}}, color = {255, 0, 255}));
  connect(Not_P201.y, FlipFlop_P201.R) annotation(
    Line(points = {{-199.6, -110}, {-182.6, -110}}, color = {255, 0, 255}));
  connect(R2B_P201.y, FlipFlop_P201.S) annotation(
    Line(points = {{-219.4, -94}, {-191.2, -94}, {-191.2, -102}, {-183, -102}}, color = {255, 0, 255}));
  connect(R2B_2_P201.y, Not_P201.u) annotation(
    Line(points = {{-219.4, -110}, {-209, -110}}, color = {255, 0, 255}));
  connect(FlipFlop_V206.Q, B2R_V206.u) annotation(
    Line(points = {{-169.4, -70.4}, {-153.4, -70.4}}, color = {255, 0, 255}));
  connect(Not_V206.y, FlipFlop_V206.R) annotation(
    Line(points = {{-199.6, -78}, {-182.6, -78}}, color = {255, 0, 255}));
  connect(R2B_V206.y, FlipFlop_V206.S) annotation(
    Line(points = {{-219.4, -62}, {-191.2, -62}, {-191.2, -70}, {-183, -70}}, color = {255, 0, 255}));
  connect(R2B_2_V206.y, Not_V206.u) annotation(
    Line(points = {{-219.4, -78}, {-209, -78}}, color = {255, 0, 255}));
  connect(FlipFlop_V205.Q, B2R_V205.u) annotation(
    Line(points = {{-169.4, -38.4}, {-153.4, -38.4}}, color = {255, 0, 255}));
  connect(Not_V205.y, FlipFlop_V205.R) annotation(
    Line(points = {{-199.6, -46}, {-182.6, -46}}, color = {255, 0, 255}));
  connect(R2B_V205.y, FlipFlop_V205.S) annotation(
    Line(points = {{-219.4, -30}, {-191.2, -30}, {-191.2, -38}, {-183, -38}}, color = {255, 0, 255}));
  connect(R2B_2_V205.y, Not_V205.u) annotation(
    Line(points = {{-219.4, -46}, {-209, -46}}, color = {255, 0, 255}));
  connect(FlipFlop_V204.Q, B2R_V204.u) annotation(
    Line(points = {{-169.4, -6.4}, {-153.4, -6.4}}, color = {255, 0, 255}));
  connect(Not_V204.y, FlipFlop_V204.R) annotation(
    Line(points = {{-199.6, -14}, {-182.6, -14}}, color = {255, 0, 255}));
  connect(R2B_V204.y, FlipFlop_V204.S) annotation(
    Line(points = {{-219.4, 2}, {-191.2, 2}, {-191.2, -6}, {-183, -6}}, color = {255, 0, 255}));
  connect(R2B_2_V204.y, Not_V204.u) annotation(
    Line(points = {{-219.4, -14}, {-209, -14}}, color = {255, 0, 255}));
  connect(FlipFlop_V203.Q, B2R_V203.u) annotation(
    Line(points = {{-169.4, 25.6}, {-153.4, 25.6}}, color = {255, 0, 255}));
  connect(Not_V203.y, FlipFlop_V203.R) annotation(
    Line(points = {{-199.6, 18}, {-182.6, 18}}, color = {255, 0, 255}));
  connect(R2B_V203.y, FlipFlop_V203.S) annotation(
    Line(points = {{-219.4, 34}, {-191.2, 34}, {-191.2, 26}, {-183, 26}}, color = {255, 0, 255}));
  connect(R2B_2_V203.y, Not_V203.u) annotation(
    Line(points = {{-219.4, 18}, {-209, 18}}, color = {255, 0, 255}));
  connect(FlipFlop_V209.Q, B2R_V209.u) annotation(
    Line(points = {{-169.4, -166.4}, {-153.4, -166.4}}, color = {255, 0, 255}));
  connect(Not_V209.y, FlipFlop_V209.R) annotation(
    Line(points = {{-199.6, -174}, {-182.6, -174}}, color = {255, 0, 255}));
  connect(R2B_V209.y, FlipFlop_V209.S) annotation(
    Line(points = {{-219.4, -158}, {-191.2, -158}, {-191.2, -166}, {-183, -166}}, color = {255, 0, 255}));
  connect(R2B_2_V209.y, Not_V209.u) annotation(
    Line(points = {{-219.4, -174}, {-209, -174}}, color = {255, 0, 255}));
  connect(FlipFlop_V202.Q, B2R_V202.u) annotation(
    Line(points = {{-169.4, 57.6}, {-153.4, 57.6}}, color = {255, 0, 255}));
  connect(Not_V202.y, FlipFlop_V202.R) annotation(
    Line(points = {{-199.6, 50}, {-182.6, 50}}, color = {255, 0, 255}));
  connect(R2B_V202.y, FlipFlop_V202.S) annotation(
    Line(points = {{-219.4, 66}, {-191.2, 66}, {-191.2, 58}, {-183, 58}}, color = {255, 0, 255}));
  connect(R2B_2_V202.y, Not_V202.u) annotation(
    Line(points = {{-219.4, 50}, {-209, 50}}, color = {255, 0, 255}));
  connect(FlipFlop_V201.Q, B2R_V201.u) annotation(
    Line(points = {{-169.4, 89.6}, {-153.4, 89.6}}, color = {255, 0, 255}));
  connect(Not_V201.y, FlipFlop_V201.R) annotation(
    Line(points = {{-199.6, 82}, {-182.6, 82}}, color = {255, 0, 255}));
  connect(R2B_V201.y, FlipFlop_V201.S) annotation(
    Line(points = {{-219.4, 98}, {-191.2, 98}, {-191.2, 90}, {-183, 90}}, color = {255, 0, 255}));
  connect(R2B_2_V201.y, Not_V201.u) annotation(
    Line(points = {{-219.4, 82}, {-209, 82}}, color = {255, 0, 255}));
  connect(ActuatorControl.y[1], R2B_V201.u) annotation(
    Line(points = {{-298, -40}, {-292, -40}, {-292, 90}, {-240, 90}, {-240, 98}, {-234, 98}}, color = {0, 0, 127}));
  connect(ActuatorControl.y[1], R2B_2_V201.u) annotation(
    Line(points = {{-298, -40}, {-292, -40}, {-292, 90}, {-240, 90}, {-240, 82}, {-234, 82}}, color = {0, 0, 127}));
  connect(ActuatorControl.y[2], R2B_V202.u) annotation(
    Line(points = {{-298, -40}, {-290, -40}, {-290, 58}, {-240, 58}, {-240, 66}, {-234, 66}}, color = {0, 0, 127}));
  connect(ActuatorControl.y[2], R2B_2_V202.u) annotation(
    Line(points = {{-298, -40}, {-290, -40}, {-290, 58}, {-240, 58}, {-240, 50}, {-234, 50}}, color = {0, 0, 127}));
  connect(ActuatorControl.y[3], R2B_V203.u) annotation(
    Line(points = {{-298, -40}, {-288, -40}, {-288, 26}, {-240, 26}, {-240, 34}, {-234, 34}}, color = {0, 0, 127}));
  connect(ActuatorControl.y[3], R2B_2_V203.u) annotation(
    Line(points = {{-298, -40}, {-288, -40}, {-288, 26}, {-240, 26}, {-240, 18}, {-234, 18}}, color = {0, 0, 127}));
  connect(ActuatorControl.y[6], R2B_V204.u) annotation(
    Line(points = {{-298, -40}, {-286, -40}, {-286, -6}, {-240, -6}, {-240, 2}, {-234, 2}}, color = {0, 0, 127}));
  connect(ActuatorControl.y[6], R2B_2_V204.u) annotation(
    Line(points = {{-298, -40}, {-286, -40}, {-286, -6}, {-240, -6}, {-240, -14}, {-234, -14}}, color = {0, 0, 127}));
  connect(ActuatorControl.y[5], R2B_V205.u) annotation(
    Line(points = {{-298, -40}, {-240, -40}, {-240, -30}, {-234, -30}}, color = {0, 0, 127}));
  connect(ActuatorControl.y[5], R2B_2_V205.u) annotation(
    Line(points = {{-298, -40}, {-240, -40}, {-240, -46}, {-234, -46}}, color = {0, 0, 127}));
  connect(ActuatorControl.y[4], R2B_V206.u) annotation(
    Line(points = {{-298, -40}, {-278, -40}, {-278, -70}, {-240, -70}, {-240, -62}, {-234, -62}}, color = {0, 0, 127}));
  connect(ActuatorControl.y[4], R2B_2_V206.u) annotation(
    Line(points = {{-298, -40}, {-278, -40}, {-278, -70}, {-240, -70}, {-240, -78}, {-234, -78}}, color = {0, 0, 127}));
  connect(ActuatorControl.y[8], R2B_P201.u) annotation(
    Line(points = {{-298, -40}, {-280, -40}, {-280, -102}, {-240, -102}, {-240, -94}, {-234, -94}}, color = {0, 0, 127}));
  connect(ActuatorControl.y[8], R2B_2_P201.u) annotation(
    Line(points = {{-298, -40}, {-280, -40}, {-280, -102}, {-240, -102}, {-240, -110}, {-234, -110}}, color = {0, 0, 127}));
  connect(ActuatorControl.y[9], R2B_P202.u) annotation(
    Line(points = {{-298, -40}, {-282, -40}, {-282, -134}, {-240, -134}, {-240, -126}, {-234, -126}}, color = {0, 0, 127}));
  connect(ActuatorControl.y[9], R2B_2_P202.u) annotation(
    Line(points = {{-298, -40}, {-282, -40}, {-282, -134}, {-240, -134}, {-240, -142}, {-234, -142}}, color = {0, 0, 127}));
  connect(ActuatorControl.y[7], R2B_V209.u) annotation(
    Line(points = {{-298, -40}, {-284, -40}, {-284, -166}, {-240, -166}, {-240, -158}, {-234, -158}}, color = {0, 0, 127}));
  connect(ActuatorControl.y[7], R2B_2_V209.u) annotation(
    Line(points = {{-298, -40}, {-284, -40}, {-284, -166}, {-240, -166}, {-240, -174}, {-234, -174}}, color = {0, 0, 127}));
  connect(V209.opening, B2R_V209.y) annotation(
    Line(points = {{120, -6}, {120, 6}, {156, 6}, {156, -166}, {-140, -166}}, color = {0, 0, 127}));
  connect(B2R_P202.y, P202_Characteristic.u) annotation(
    Line(points = {{-140, -134}, {20, -134}, {20, -70}, {34, -70}}, color = {0, 0, 127}));
  connect(B2R_P201.y, P201_Characteristic.u) annotation(
    Line(points = {{-140, -102}, {-112, -102}, {-112, -70}, {-102, -70}}, color = {0, 0, 127}));
  connect(B2R_V201.y, V201.opening) annotation(
    Line(points = {{-140, 90}, {-120, 90}, {-120, -12}, {-92, -12}}, color = {0, 0, 127}));
  connect(B2R_V202.y, V202.opening) annotation(
    Line(points = {{-140, 58}, {-118, 58}, {-118, -10}, {-54, -10}}, color = {0, 0, 127}));
  connect(B2R_V203.y, V203.opening) annotation(
    Line(points = {{-140, 26}, {-116, 26}, {-116, -8}, {-18, -8}}, color = {0, 0, 127}));
  connect(B2R_V206.y, V206.opening) annotation(
    Line(points = {{-140, -70}, {-122, -70}, {-122, 66}, {-18, 66}}, color = {0, 0, 127}));
  connect(B2R_V205.y, V205.opening) annotation(
    Line(points = {{-140, -38}, {-124, -38}, {-124, 68}, {-54, 68}}, color = {0, 0, 127}));
  connect(B2R_V204.y, V204.opening) annotation(
    Line(points = {{-140, -6}, {-126, -6}, {-126, 70}, {-92, 70}}, color = {0, 0, 127}));
  connect(V204.port_b, pipe_V206_B201.port_a) annotation(
    Line(points = {{-88, 64}, {-88, 56}}, color = {0, 127, 255}));
  annotation(
    uses(Modelica(version = "4.0.0")),
 //good results with IDA, max 1 Integration and 1 Processor. Still need to figure out optimal solver setup
 // cvode produces veery fast results
    Diagram(coordinateSystem(extent = {{-320, 120}, {160, -180}})),
    version = "",
    experiment(StartTime = 0, StopTime = 600, Tolerance = 1e-06, Interval = 1),
    __OpenModelica_commandLineOptions = "--matchingAlgorithm=PFPlusExt --indexReductionMethod=dynamicStateSelection -d=initialization,NLSanalyticJacobian",
    __OpenModelica_simulationFlags(lv = "LOG_STATS", s = "ida", variableFilter = ".*level|.*flow|.*opening|.*p|.*N"));
end ModVA_online_stable;
