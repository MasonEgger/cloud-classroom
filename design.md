# Cloud Classroom Design Document

## Vision

Cloud Classroom eliminates the barriers that prevent educators from incorporating hands-on cloud computing experiences into their curriculum by providing a controlled, cost-effective proxy between students and cloud infrastructure.

## Problem Statement

### The Challenge

Educators want to teach practical cloud computing skills using real cloud infrastructure, but face significant obstacles:

1. **Financial Barriers**: Cloud platforms require credit cards and billing information, creating liability for educational institutions
2. **Resource Management Complexity**: Tracking and controlling cloud resource usage across multiple students is difficult
3. **Administrative Overhead**: Setting up accounts, managing access, and ensuring proper resource cleanup is time-consuming
4. **Cost Unpredictability**: Students may accidentally create expensive resources or forget to clean up after exercises
5. **Access Control**: Ensuring students can only access their assigned resources and appropriate cloud services

### The Impact

Without a solution, educators either:
- Avoid teaching cloud computing entirely, leaving students unprepared for modern infrastructure
- Use simulators that don't provide real-world experience
- Require students to use personal credit cards, creating equity and liability issues
- Spend excessive time on administrative tasks instead of teaching

## Solution Overview

Cloud Classroom acts as an intelligent intermediary that provides students with supervised access to real cloud infrastructure while maintaining institutional control over resources and costs.

### Core Value Propositions

1. **Zero Student Financial Commitment**: Students get hands-on cloud experience without needing personal payment methods
2. **Institutional Cost Control**: Educators set spending limits and resource constraints before any resources are provisioned
3. **Automated Resource Management**: The system handles provisioning, monitoring, and cleanup of cloud resources
4. **Educational Focus**: Instructors spend time teaching rather than managing infrastructure
5. **Real-World Experience**: Students work with actual cloud platforms, not simulations

## User Personas

### Primary Users

**The Workshop Instructor**
- Runs short-term technical workshops (1-3 days)
- Needs quick student onboarding without complex registration
- Wants to focus on teaching, not infrastructure management
- Wants to auto provision infrastructure according to a set of requirements
- Requires cost predictability and resource limits

**The Academic Educator**
- Teaches semester-long courses involving cloud computing
- Manages multiple classes with different resource requirements
- Needs detailed resource tracking and student progress monitoring
- Requires integration with existing educational workflows

### Secondary Users

**The Student**
- Wants to learn cloud technologies hands-on
- Needs simple access to resources without complex setup
- Expects their learning environment to work reliably
- Expects to be able to spin up and tear down resources required at will
- Values having their own dedicated resources during exercises

**The IT Administrator**
- Ensures institutional security and compliance requirements are met
- Monitors overall resource usage and costs
- Manages instructor access and permissions
- Handles troubleshooting and support escalation

## Jobs to Be Done

### For Educators

**When I'm planning a cloud computing lesson, I want to:**
- Define exactly what cloud resources students will need
- Have a way to provide automations to run that will provision the resources after they are created
- Set clear limits on resource usage and costs
- Create a class environment that students can join easily
- Know that resources will be automatically cleaned up afterward

**When I'm teaching a workshop or a semester course, I want to:**
- Get students connected to their resources in minutes, not hours
- Focus on the learning objectives rather than troubleshooting access issues
- Have confidence that no student can exceed the budget I've set
- Monitor student progress and resource usage in real-time
- Gain access to the student environment for troubleshooting
- Ensure students can't interfere with each other's work
- Create different resource configurations for different assignments

### For Students

**When I'm starting a cloud computing exercise, I want to:**
- Get immediate access to my assigned resources
- Have clear connection information and credentials
- Work in an environment that's identical to what my classmates have
- Focus on learning rather than fighting with setup issues

**When I'm working on assignments, I want to:**
- Have dedicated resources that won't be affected by other students
- Be able to restart or reset my environment if something goes wrong
- Access my resources from anywhere with an internet connection
- Not worry about accidentally creating expensive resources

### For Institutions

**When evaluating cloud education tools, we want to:**
- Maintain full control over spending and resource allocation
- Ensure student data and work remains secure and isolated
- Meet compliance requirements for educational technology
- Scale efficiently from small workshops to large courses

**When operating the platform, we want to:**
- Have detailed audit trails of all resource usage and costs
- Monitor system health and student experience
- Quickly resolve any technical issues that arise
- Integrate smoothly with existing educational systems

## User Workflows

### Workshop Mode (Simple)

1. **Instructor Setup**
   - Creates a workshop with resource specifications
   - Creates an auto-provisioning script for software installation and other post-resource creation tasks
   - Generates a simple access code
   - Sets resource limits and duration

2. **Student Registration**
   - Enters workshop code and basic information
   - Instructor approves enrollment requests or can set to auto approve
   - Can create cloud resources according to their allocation

3. **During Workshop**
   - Students work with real cloud infrastructure
   - Instructor monitors resource usage and student progress
   - System enforces resource limits automatically

4. **Workshop Completion**
   - All student resources are automatically destroyed
   - Final usage report generated for instructor

### Academic Course Mode (Advanced)

1. **Course Planning**
   - Instructor creates multiple classes with different configurations
   - Defines resource templates for different types of assignments
   - Sets up gradual resource access as course progresses

2. **Student Enrollment**
   - Students register with email verification
   - Instructor approves enrollment requests
   - Students gain access to appropriate resources based on course schedule

3. **Assignment Lifecycle**
   - Instructor activates resources for specific assignments
   - Students complete hands-on work with dedicated infrastructure
   - System tracks completion and resource usage
   - Resources are cleaned up after assignment deadline

4. **Course Management**
   - Ongoing monitoring of student progress and resource usage
   - Ability to adjust resource allocations based on learning needs

## Success Metrics

### Educational Outcomes
- Increase in hands-on cloud computing exercises in curriculum
- Student confidence and competency with cloud platforms
- Instructor satisfaction with teaching effectiveness
- Reduction in time spent on infrastructure management

### Operational Efficiency
- Time from student registration to resource access
- Percentage of successful student connections on first attempt
- Instructor time saved on administrative tasks
- Resource utilization efficiency

### Risk Management
- Zero incidents of budget overruns
- Complete resource cleanup after exercises
- Maintained security and compliance standards
- Student data protection and privacy

## Design Principles

### Simplicity First
Every interaction should be as simple as possible. Complex cloud concepts should be abstracted away until students are ready to learn them.

### Safety by Default
The system should make it impossible for students to accidentally create expensive resources or access inappropriate services.

### Educational Transparency
While abstracting complexity, the system should still expose real cloud concepts and terminology to maintain educational value.

### Institutional Control
Educational institutions must maintain complete visibility and control over costs, resources, and student data.

### Scalable Architecture
The platform should efficiently handle everything from 10-student workshops to 500-student courses without architectural changes.

## Future Considerations

### Multi-Cloud Support
Expanding beyond a single cloud provider to support educational diversity and prevent vendor lock-in.

### Advanced Analytics
Detailed learning analytics to help instructors understand how students interact with cloud resources and where they struggle.

### Assessment Integration
Automated grading capabilities based on curriculum requirements to support a certification effort.

### Collaborative Features
Support for team-based projects and shared resource environments while maintaining security isolation.

## Implementation Details

### Design Principles
- Simple and elegant
- Modern
- Modular, allow for configuration of title, text, colors, and any image via a config file

### Architecture
- Microservice architecture
- Communication should happen via gRPC
- Automatic documentation of all API endpoints

### Frontend
- Follow modern web design principles
- Use HTMX as much as possible.
- When Javascript is required, use Alpine.js
- Use Tailwind CSS for UI components and styling 

### Cloud Provider
- Modular design for later support for multiple cloud providers
- Start with DigitalOcean

### Backend
- Implement using FastAPI
- Default to SQLite for deployment, but offer options for common databases7
- Use modern deployment methods for deciding how to run the ASGI, if an ASGI is still the correct way
- Provisioning after setup is done via Ansible playbooks using cloud init
   - Known as "user data" in DigitalOcean

### Deployment
- Bare metal deployment options, orchestrated using Ansible
- Docker compose
- Helm chart
