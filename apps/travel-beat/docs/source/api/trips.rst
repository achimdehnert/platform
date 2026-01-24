Trips API
=========

Models
------

.. automodule:: apps.trips.models
   :members:
   :undoc-members:
   :show-inheritance:

Trip Model
~~~~~~~~~~

The Trip model represents a user's travel itinerary.

**Fields:**

- ``name`` - Trip name/title
- ``user`` - Owner (ForeignKey to User)
- ``origin`` - Starting location
- ``start_date`` - Trip start date
- ``end_date`` - Trip end date
- ``trip_type`` - solo/couple/family/group
- ``protagonist_name`` - Story protagonist name
- ``protagonist_gender`` - Story protagonist gender
- ``user_notes`` - Additional notes for AI

Stop Model
~~~~~~~~~~

The Stop model represents individual destinations within a trip.

**Fields:**

- ``trip`` - Parent trip (ForeignKey)
- ``location`` - Destination name
- ``arrival_date`` - Arrival date
- ``departure_date`` - Departure date
- ``highlights`` - Key activities/sights
- ``notes`` - Additional notes
- ``order`` - Sort order within trip

Views
-----

.. automodule:: apps.trips.views
   :members:
   :undoc-members:

Wizard Views
~~~~~~~~~~~~

The trip creation wizard is implemented in ``apps.trips.wizard``:

- ``wizard_step1`` - Trip basics form
- ``wizard_step2`` - Destinations/stops
- ``wizard_step3`` - Story settings
- ``wizard_step4`` - Review and generate

Forms
-----

.. automodule:: apps.trips.forms
   :members:
   :undoc-members:

**TripBasicsForm**
   Step 1 form for basic trip information

**StopForm**
   Individual stop/destination form

**StopFormSet**
   Formset for managing multiple stops

URL Patterns
------------

.. code-block:: python

   /trips/                    # Trip list
   /trips/<id>/               # Trip detail
   /trips/wizard/step1/       # Wizard step 1
   /trips/wizard/step2/       # Wizard step 2
   /trips/wizard/step3/       # Wizard step 3
   /trips/wizard/step4/       # Wizard step 4
