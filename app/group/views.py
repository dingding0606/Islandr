'''
@Description: View file for group blueprint
@Author: Tianyi Lu
@Date: 2019-07-05 14:59:30
@LastEditors: Tianyi Lu
@LastEditTime: 2019-09-01 14:24:06
'''

from flask import render_template, abort, url_for, request, redirect, flash, current_app, Markup
from flask_login import login_required, current_user
from . import group
from .. import db
from ..models import Group, Post, User, Join
from ..search_index import update_index
from ..decorators import admin_required, owner_required
from ..image_saver import saver, deleter
import os, shutil

@group.route('/all')
@login_required
def all_group():
    page = request.args.get('page', 1, type=int)
    pagination = Group.query.filter_by(is_approved=1).order_by(Group.groupname).paginate(page, per_page=12,
                                      error_out = False)
    groups = pagination.items
    return render_template('all_group.html', groups=groups, pagination=pagination)

@group.route('/<int:id>')
@login_required
def group_profile(id):
    group = Group.query.get_or_404(id)

    if group.is_approved != 1 and current_user.id != group.owner[0].id and current_user.is_admin == False:
        abort(403)
    page = request.args.get('page', 1, type=int)

    if not current_user.id == group.owner[0].id:
        group.posts = group.posts.filter_by(is_approved=1)
    pagination = group.posts.order_by(Post.last_modified.desc()).paginate(
        page, per_page=current_app.config['FLASKY_POSTS_PER_PAGE'],
        error_out = False)
    users=[]
    joins = group.members.filter_by(is_approved=1).all()

    for join in joins:
        user = User.query.get_or_404(join.user_id)
        users.append(user)

    vision_html = Markup(group.vision_goal.replace('\r\n', '<br/>'))
    routine_html = Markup(group.routine_events.replace('\r\n', '<br/>'))
    join_html = Markup(group.look_for.replace('\r\n', '<br/>'))

    posts = pagination.items
    logo = url_for('static', filename="group_logo/"+group.logo)
    background = url_for('static', filename="group_background_pic/"+group.background)
    return render_template('group_profile.html', users=users, group=group, posts=posts,logo=logo, background=background,
                           pagination=pagination, vision_html=vision_html, routine_html=routine_html, join_html=join_html)

@group.route('/approve')
@login_required
def group_approve():
    group = Group.query.filter_by(is_approved=0).order_by(Group.create_date.desc())
    page = request.args.get('page', 1, type=int)
    pagination = group.paginate(page, per_page=12, error_out=False)
    groups = pagination.items
    return render_template('group_approve.html', groups=groups, pagination=pagination)

@group.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def group_profile_edit(id):
    old_group = Group.query.get_or_404(id)

    if old_group.owner[0].id != current_user.id:
        abort(403)

    if request.method == 'POST':
        if not request.form['groupname']:
            flash("Please fill in the name!", 'danger')
            return redirect(url_for('.group_profile_edit'))

        if request.files['logo']:
            logo = request.files['logo']
            if old_group.logo != 'default.jpg':
                deleter('group_logo', old_group.logo)
            new_logo_filename = saver('group_logo', logo)
            old_group.logo = new_logo_filename

        if request.files['background']:
            background = request.files['background']
            if old_group.background != 'default.jpg':
                deleter('group_background', old_group.background)
            new_background_filename = saver('group_background', background)
            old_group.background = new_background_filename

        if request.files['proposal']:
            proposal_file = request.files['proposal']
            _, ext = os.path.splitext(proposal_file.filename)
            proposal_filename = str(old_group.id) + '_UWCCSC_TEAM_PROPOSAL' + str(ext)
            proposal_dir = os.path.join(current_app.root_path, 'static', 'files', str(old_group.id), proposal_filename)
            proposal_file.save(proposal_dir)
            old_group.proposal_file = proposal_filename

        old_group.groupname = request.form['groupname']
        old_group.vision_goal = request.form['vision']
        old_group.routine_events = request.form['routine']
        old_group.look_for = request.form['join']

        db.session.add(old_group)
        db.session.commit()
        update_index(Group)

        return redirect(url_for('.group_profile', id=old_group.id))
    return render_template('creater.html', old_group=old_group)

@group.route('/<int:id>/join')
@login_required
def group_join(id):
    group = Group.query.get_or_404(id)
    join = Join(group=group, member=current_user)
    db.session.add(join)
    db.session.commit()
    flash('Your application has been sent to group leader.', 'warning')
    return redirect(url_for('group.group_profile', id=id))

@group.route('/<int:id>/leave')
@login_required
def group_leave(id):
    group = Group.query.get_or_404(id)
    if group.owner[0].id == current_user.id:
        abort(403)
    join = Join.query.filter_by(group_id=group.id, user_id=current_user.id).first()
    db.session.delete(join)
    db.session.commit()
    return redirect(url_for('group.group_profile', id=id))

@group.route('/<int:id>/approved')
@login_required
@admin_required
def group_approved(id):
    group = Group.query.get_or_404(id)
    if group.is_approved == 0:
        group.is_approved = 1
    elif group.is_approved == -1:
        return redirect(url_for('group.group_rejected', id=id))
    db.session.add(group)
    # send group approved message to group owner
    group.owner[0].add_msg({'role': 'notification',
                            'name': 'Group Approved',
                            'content': 'Your group \"%s\" has been approved' % group.groupname})
    db.session.commit()
    return render_template('group_approved.html')

@group.route('/<int:id>/rejected', methods=['GET', 'POST'])
@login_required
@admin_required
def group_rejected(id):
    group = Group.query.get_or_404(id)
    if group.is_approved == 0:
        group.is_approved = -1
    elif group.is_approved == 1:
        return redirect(url_for('group.group_approved', id=id))

    if request.method == 'POST':
        group.reject_msg = request.form['comment']
        # print(post.reject_msg)
        db.session.add(group)
        db.session.commit()
        return redirect(url_for('group.group_approve'))

    db.session.add(group)
    group.owner[0].add_msg({'role': 'notification',
                            'name': 'Group Rejected',
                            'content': 'Sorry, your group \"%s\" has been rejected.' % group.groupname})
    db.session.commit()
    return render_template('group_rejected.html')

@group.route('/application/<int:group_id>/<int:user_id>/approve')
@login_required
def application_approve(group_id, user_id):
    join = Join.query.filter_by(group_id=group_id, user_id=user_id).first()
    if not join:
        abort(404)
    if join.group.owner[0].id != current_user.id:
        abort(403)
    join.is_approved = 1
    #send approve message
    applicant = User.query.get(join.user_id)
    group = Group.query.get(join.group_id)
    applicant.add_msg({'role': 'notification',
                       'name': 'Application Approved',
                       'content': 'Your have successfully joined \"%s\" Team!' % group.groupname})
    db.session.commit()
    return redirect(url_for('main.message', ctype='my_group'))

@group.route('/application/<int:group_id>/<int:user_id>/reject')
@login_required
def application_reject(group_id, user_id):
    join = Join.query.filter_by(group_id=group_id, user_id=user_id).first()
    if not join:
        abort(404)
    if join.group.owner[0].id != current_user.id:
        abort(403)
    db.session.delete(join)
    # send rejected message
    applicant = User.query.get(join.user_id)
    group = Group.query.get(join.group_id)
    applicant.add_msg({'role': 'notification',
                       'name': 'Application Rejected',
                       'content': 'Sorry, Your have been rejected by \"%s\" Team!' % group.groupname})
    db.session.commit()
    return redirect(url_for('main.message', ctype='my_group'))

@group.route('/<int:id>/delete/<user_hex>')
@login_required
def group_delete(id, user_hex):
    old_group = Group.query.get_or_404(id)

    if old_group.owner[0].id != current_user.id or user_hex != old_group.owner[0].user_hex :
        abort(403)

    for post in old_group.posts:
        db.session.delete(post)

    for moment in old_group.moments:
        db.session.delete(moment)

    moments_dir = os.path.join(current_app.root_path, 'static/moments', str(old_group.id))
    if os.path.isdir(moments_dir):
        shutil.rmtree(moments_dir)

    files_dir = os.path.join(current_app.root_path, 'static', 'files', str(old_group.id))
    if os.path.isdir(files_dir):
        shutil.rmtree(files_dir)

    db.session.delete(old_group)
    db.session.commit()

    flash('Your group %s has been deleted!' % str(old_group.groupname), 'success')
    return redirect(url_for('main.index'))

@group.route('<int:id>/members')
@login_required
def group_members(id):
    group = Group.query.get_or_404(id)
    page = request.args.get('page', 1, type=int)
    pagination = group.members.filter_by(is_approved=1).paginate(page, per_page=12, error_out=False)
    users = []
    for item in pagination.items:
        user = User.query.get_or_404(item.user_id)
        users.append(user)
    member_amount = len(users)
    return render_template('group_members.html', group=group, pagination=pagination, users=users, member_amount=member_amount)

@group.route('/remove/<int:group_id>/<int:user_id>')
@login_required
@owner_required
def remove_member(group_id, user_id):
    if current_user.my_group.id != group_id:
        abort(403)
    user = User.query.get_or_404(user_id)
    join = Join.query.filter_by(group_id=group_id, user_id=user_id).first()
    if not join:
        abort(404)
    db.session.delete(join)
    db.session.commit()

    flash('Your have removed %s from your group' % (user.username), 'success')

    return redirect(url_for('group.group_members', id=group_id))

@group.route('/transfer/<int:group_id>/<int:user_id>')
@login_required
@owner_required
def transfer_owner(group_id, user_id):
    if current_user.my_group.id != group_id:
        abort(403)

    group = Group.query.get_or_404(group_id)
    new_owner = User.query.get_or_404(user_id)
    group.owner[0] = new_owner
    db.session.commit()

    flash('Your have transferred your ownership of %s to %s' % (group.groupname, new_owner.username), 'success')

    return redirect(url_for('group.group_members', id=group_id))
