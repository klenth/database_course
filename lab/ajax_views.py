from django.shortcuts import render, get_object_or_404
from django.views.decorators import csrf as csrf_decorators
from django.http import Http404, JsonResponse
import django.contrib.auth.decorators as auth_decorators
import json
from .models import *
from . import errors


@auth_decorators.login_required
def instructor_update_problem(request, problem_id):
    if request.method != 'POST':
        raise Http404

    instructor = get_object_or_404(Instructor, id=request.user.id)
    problem = get_object_or_404(Problem, pk=problem_id)
    if problem.lab().course.instructor != instructor:
        raise Http404

    if request.content_type == 'application/json':
        try:
            data = json.loads(request.body)

            if 'new_title' in data:
                problem.title = data['new_title']
            if 'new_prompt' in data:
                problem.prompt = data['new_prompt']
            if 'new_starter_code' in data:
                problem.starter_code = data['new_starter_code']
            if 'new_solution' in data:
                problem.solution = data['new_solution']
            if 'new_after_code' in data:
                problem.after_code = data['new_after_code']
            if 'new_schema_id' in data:
                schema = get_object_or_404(ProblemSchema, pk=data['new_schema_id'])
                problem.set_schema(schema)

            # Reset saved results for this problem if something that would affect them has changed
            # (No need to do this for schema because problem.set_schema() already does)
            if 'new_solution' in data \
                    or 'new_after_code' in data:
                problem.reset_results()

            problem.save()

            return JsonResponse({})
        except ValueError as e:
            import sys
            print(e, file=sys.stderr)
            return JsonResponse({
                'error': 'Unable to parse data'
            })
    else:
        raise Http404


@auth_decorators.login_required
def instructor_upload_schema(request):
    get_object_or_404(Instructor, id=request.user.id)

    if 'schema_file' in request.FILES:
        schema_file = request.FILES['schema_file']
        ps = ProblemSchema.create_from_upload(schema_file)

        return JsonResponse({
            'new_schema': {
                'id': ps.id,
                'filename': ps.filename
            }
        })

    else:
        raise Http404


@auth_decorators.login_required
def instructor_check_schema_status(request):
    if request.content_type != 'application/json':
        raise Http404

    get_object_or_404(Instructor, id=request.user.id)

    print(request.body)

    params = json.loads(request.body)
    if not 'schema_id' in params:
        raise Http404
    schema_id = params['schema_id']

    schema = get_object_or_404(ProblemSchema, pk=schema_id)

    return JsonResponse({
        'filename': schema.filename,
        'status': schema.get_status_display(),
        'table_names': schema.get_table_names()
    })


@auth_decorators.login_required
def instructor_get_data_files(request, problem_id):
    problem = get_object_or_404(Problem, pk=problem_id)
    instructor = get_object_or_404(Instructor, id=request.user.id)

    if problem.lab().course.instructor != instructor:
        raise Http404

    data_files = problem.table_data.all()

    return JsonResponse({
        'data_files': [
            {
                'id': df.id,
                'filename': df.data_filename,
            } for df in data_files
        ]
    })


@auth_decorators.login_required
def instructor_upload_data_file(request, problem_id):
    problem = get_object_or_404(Problem, pk=problem_id)
    instructor = get_object_or_404(Instructor, id=request.user.id)

    if problem.lab().course.instructor != instructor:
        raise Http404

    if 'data_file' in request.FILES:
        data_file = request.FILES['data_file']
        ptd = ProblemTableData(problem=problem, data_filename=data_file.name)
        ptd.data_file.save(name=str(uuid.uuid1()), content=data_file)
        ptd.save()

        return JsonResponse({
            'new_data_file': {
                'id': ptd.id,
                'filename': ptd.data_filename
            }
        })

    else:
        raise Http404


@auth_decorators.login_required
def instructor_remove_data_file(request, problem_id):
    if request.method != 'POST':
        raise Http404
    problem = get_object_or_404(Problem, pk=problem_id)
    instructor = get_object_or_404(Instructor, id=request.user.id)

    if problem.lab().course.instructor != instructor:
        raise Http404

    data = json.loads(request.body)
    if 'data_file_id' not in data:
        raise Http404
    data_file_id = data['data_file_id']

    data_file = get_object_or_404(ProblemTableData, pk=data_file_id)

    if problem.id != data_file.problem.id:
        raise Http404

    data_file.delete()
    print(f'Deleted ProblemTableData with id={data_file_id}')

    return JsonResponse({})


@auth_decorators.login_required
def instructor_get_test_cases(request, problem_id):
    problem = get_object_or_404(Problem, pk=problem_id)
    instructor = get_object_or_404(Instructor, id=request.user.id)

    if problem.lab().course.instructor != instructor:
        raise Http404

    test_cases = problem.test_cases.all()

    table_names = problem.schema.get_table_names() if problem.schema else ()

    return JsonResponse({
        'test_cases': [
            {
                'id': tc.id,
                'title': tc.title,
                'description': tc.description,
                'number': tc.number,
                'points': tc.points,
                'type': tc.type,
                'table_data_mapping': {
                    table_name: {
                        'id': table_data.id,
                        'filename': table_data.data_filename
                    } if table_data else None
                    for (table_name, table_data) in tc.get_table_data_mapping(table_names).items()
                }
            } for tc in test_cases
        ],
        'data_files': [
            {
                'id': td.id,
                'filename': td.data_filename,
            } for td in problem.table_data.all()
        ]
    })


@auth_decorators.login_required
def instructor_add_test_case(request, problem_id):
    if request.method != 'POST':
        raise Http404

    problem = get_object_or_404(Problem, pk=problem_id)
    instructor = get_object_or_404(Instructor, id=request.user.id)

    if problem.lab().course.instructor != instructor:
        raise Http404

    ptc = problem.add_new_test_case()
    return JsonResponse({
        'new_test_case': {
            'id': ptc.id,
            'title': ptc.title,
            'description': ptc.description,
            'number': ptc.number,
            'points': ptc.points,
            'type': ptc.type,
            'table_data_mapping': {
                table_name: None
                for table_name in problem.schema.get_table_names()
            },
        },
        'data_files': [
            {
                'id': td.id,
                'filename': td.data_filename,
            } for td in problem.table_data.all()
        ],
    })


@auth_decorators.login_required
def instructor_delete_test_case(request, problem_id):
    if request.method != 'POST':
        raise Http404

    problem = get_object_or_404(Problem, pk=problem_id)
    data = json.loads(request.body)
    if 'test_case_id' not in data:
        raise Http404

    test_case = get_object_or_404(ProblemTestCase, pk=data['test_case_id'])
    instructor = get_object_or_404(Instructor, id=request.user.id)

    if test_case.problem.lab().course.instructor != instructor \
            or test_case.problem != problem:
        raise Http404

    test_case.problem.delete_test_case(test_case)

    return JsonResponse({})


@auth_decorators.login_required
def instructor_update_test_case(request, problem_id):
    if request.method != 'POST':
        raise Http404

    data = json.loads(request.body)
    if 'test_case_id' not in data:
        raise Http404

    test_case = get_object_or_404(ProblemTestCase, pk=data['test_case_id'])
    instructor = get_object_or_404(Instructor, id=request.user.id)

    if test_case.problem.id != problem_id \
            or test_case.problem.lab().course.instructor != instructor:
        raise Http404

    result_needs_reset = False

    if 'new_title' in data:
        test_case.title = data['new_title']
    if 'new_description' in data:
        test_case.description = data['new_description']
    if 'new_points' in data:
        test_case.points = int(data['new_points'])
    if 'new_type' in data and data['new_type'] != test_case.type:
        test_case.type = data['new_type']
        result_needs_reset = True
    if 'new_table_data_mapping' in data:
        for table_name, data_id in data['new_table_data_mapping'].items():
            maybe_ptctd = test_case.table_data_set.filter(table_name=table_name)
            if maybe_ptctd.exists():
                ptctd = maybe_ptctd.get()
                if ptctd.table_data.id != data_id:
                    if data_id is None:
                        ptctd.delete()
                    else:
                        ptctd.table_data = get_object_or_404(ProblemTableData, pk=data_id)
                        ptctd.save()
            elif data_id is not None:
                table_data = get_object_or_404(ProblemTableData, pk=data_id)
                ptctd = ProblemTestCaseTableData(test_case=test_case, table_name=table_name, table_data=table_data)
                ptctd.save()
        result_needs_reset = True

    if result_needs_reset:
        test_case.reset_result()

    test_case.save()

    return JsonResponse({})


@auth_decorators.login_required
def instructor_validate_problem(request, problem_id):
    if request.method != 'POST':
        raise Http404

    problem = get_object_or_404(Problem, pk=problem_id)
    instructor = get_object_or_404(Instructor, id=request.user.id)

    if problem.lab().course.instructor != instructor:
        raise Http404

    error_messages = []

    if not problem.solution:
        error_messages.append('No solution specified')
    if not problem.test_cases.exists():
        error_messages.append('No test cases given')

    try:
        labs.compute_results(problem)
    except errors.ProblemError as e:
        error_messages.append(str(e))

    return JsonResponse({
        'errors': error_messages
    })


@auth_decorators.login_required
def instructor_view_markdown(request, problem_id):
    from lab.templatetags import custom_tags

    if request.method != 'POST':
        raise Http404

    problem = get_object_or_404(Problem, pk=problem_id)
    instructor = get_object_or_404(Instructor, id=request.user.id)

    if problem.lab().course.instructor != instructor:
        raise Http404

    error_messages = []
    html = ''

    input = json.loads(request.body)

    if 'markdown' not in input:
        error_messages.append('No markdown text given')
    else:
        md = input['markdown']
        html = str(custom_tags.markdown(md))

    return JsonResponse({
        'errors': error_messages,
        'html': html,
    })
