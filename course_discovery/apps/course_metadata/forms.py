from django import forms
from django.core.exceptions import ValidationError
from django.forms.utils import ErrorList
from django.utils.translation import gettext_lazy as _
from slugify import slugify

from course_discovery.apps.course_metadata.choices import ProgramStatus
from course_discovery.apps.course_metadata.models import Course, CourseRun, Pathway, Program
from course_discovery.apps.course_metadata.widgets import SortedModelSelect2Multiple


PROGRAM_OVERVIEW_MAX_LENGTH = 750


class ProgramAdminForm(forms.ModelForm):
    class Meta:
        model = Program
        fields = '__all__'

        widgets = {
            'courses': SortedModelSelect2Multiple(
                url='admin_metadata:course-autocomplete',
                attrs={
                    'data-minimum-input-length': 3,
                    'class': 'sortable-select',
                },
            ),
            'authoring_organizations': SortedModelSelect2Multiple(
                url='admin_metadata:organisation-autocomplete',
                attrs={
                    'data-minimum-input-length': 2,
                    'class': 'sortable-select',
                },
                forward=['product_source'],
            ),
            'credit_backing_organizations': SortedModelSelect2Multiple(
                url='admin_metadata:organisation-autocomplete',
                attrs={
                    'data-minimum-input-length': 2,
                    'class': 'sortable-select',
                },
                forward=['product_source'],
            ),
            'instructor_ordering': SortedModelSelect2Multiple(
                url='admin_metadata:person-autocomplete',
                attrs={
                    'data-minimum-input-length': 3,
                    'class': 'sortable-select',
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['type'].required = True
        self.fields['marketing_slug'].required = False
        self.fields['courses'].required = False
        if self.fields.get('product_source'):
            self.fields['product_source'].required = True
        self.fields['overview'].help_text = (
            f'Maximum {PROGRAM_OVERVIEW_MAX_LENGTH} characters.'
        )

    def clean(self):

        super().clean()

        status = self.cleaned_data.get('status')
        banner_image = self.cleaned_data.get('banner_image')

        if status == ProgramStatus.Active and not banner_image:
            raise ValidationError(_(
                'Programs can only be activated if they have a banner image.'
            ))

        return self.cleaned_data

    def clean_marketing_slug(self):
        marketing_slug = self.cleaned_data.get('marketing_slug')

        if not marketing_slug:
            title = self.cleaned_data.get('title') or self.instance.title
            program_type = self.cleaned_data.get('type') or self.instance.type
            organizations = self.cleaned_data.get('authoring_organizations')
            organization = organizations[0] if organizations else None

            if program_type and organization:
                base_slug = f'{program_type.slug}/{organization.slug}-{slugify(title)}'
            else:
                base_slug = slugify(title)

            marketing_slug = base_slug
            suffix = 1

            while Program.objects.filter(marketing_slug=marketing_slug).exclude(pk=self.instance.pk).exists():
                marketing_slug = f'{base_slug}-{suffix}'
                suffix += 1

        return marketing_slug

    def clean_authoring_organizations(self):
        """
        Checks the presence of images of logos of certificates of author orgs.

        Iterates through authoring organizations and throws a ValidationError
        if any organization does not have a certificate logo image.
        """
        authoring_organizations = self.cleaned_data.get('authoring_organizations')
        orgs_with_empty_certificate_logo_image = []

        for organization in authoring_organizations:
            if not organization.certificate_logo_image:
                orgs_with_empty_certificate_logo_image.append(organization.name)

        if orgs_with_empty_certificate_logo_image:
            error_message = f'Certificate logo image cannot be empty for organizations: ' \
                            f'{", ".join(orgs_with_empty_certificate_logo_image)}.'
            raise ValidationError(error_message)

        return authoring_organizations

    def clean_overview(self):
        overview = self.cleaned_data.get('overview') or ''

        if len(overview) > PROGRAM_OVERVIEW_MAX_LENGTH:
            raise ValidationError(
                f'Overview cannot exceed {PROGRAM_OVERVIEW_MAX_LENGTH} characters '
                f'(currently {len(overview)}).'
            )

        return overview


class CourseRunSelectionForm(forms.ModelForm):
    class Meta:
        model = Program
        fields = ('excluded_course_runs',)

    def __init__(self, data=None, files=None, auto_id='id_%s', prefix=None, initial=None, error_class=ErrorList,
                 label_suffix=':', empty_permitted=False, instance=None):
        super().__init__(
            data, files, auto_id, prefix,
            initial, error_class, label_suffix,
            empty_permitted, instance
        )

        query_set = [course.pk for course in instance.courses.all()]
        self.fields['excluded_course_runs'].widget = forms.widgets.CheckboxSelectMultiple()
        self.fields['excluded_course_runs'].help_text = ''
        self.fields['excluded_course_runs'].queryset = CourseRun.objects.filter(
            course__id__in=query_set
        )


class CourseAdminForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = '__all__'
        exclude = ('slug', 'url_slug', )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.fields.get('product_source'):
            self.fields['product_source'].required = True


class CourseRunAdminForm(forms.ModelForm):
    class Meta:
        model = CourseRun
        fields = '__all__'
        widgets = {
            'staff': SortedModelSelect2Multiple(
                url='admin_metadata:person-autocomplete',
                attrs={
                    'data-minimum-input-length': 3,
                    'class': 'sortable-select',
                },
            ),
            'transcript_languages': SortedModelSelect2Multiple(
                url='language_tags:language-tag-autocomplete',
                attrs={
                    'data-minimum-input-length': 3,
                    'class': 'sortable-select',
                },
            ),
            'video_translation_languages': SortedModelSelect2Multiple(
                url='language_tags:language-tag-autocomplete',
                attrs={
                    'data-minimum-input-length': 3,
                    'class': 'sortable-select',
                },
            ),
        }


class PathwayAdminForm(forms.ModelForm):
    class Meta:
        model = Pathway
        fields = '__all__'

    def clean(self):
        partner = self.cleaned_data.get('partner')
        programs = self.cleaned_data.get('programs')

        # partner and programs are required. If they are missing, skip this check and just show the required error
        if partner and programs:
            Pathway.validate_partner_programs(partner, programs)

        return self.cleaned_data


class ExcludeSkillsForm(forms.Form):
    """
    Form to handle excluding skills from course.
    """
    exclude_skills = forms.MultipleChoiceField()
    include_skills = forms.MultipleChoiceField()

    def __init__(self, course_skills, excluded_skills, *args, **kwargs):
        """
        Initialize multi choice fields.
        """
        super().__init__(*args, **kwargs)
        self.fields['exclude_skills'] = forms.MultipleChoiceField(
            choices=((course_skill.skill.id, course_skill.skill.name) for course_skill in course_skills),
            required=False,
        )
        self.fields['include_skills'] = forms.MultipleChoiceField(
            choices=((course_skill.skill.id, course_skill.skill.name) for course_skill in excluded_skills),
            required=False,
        )
